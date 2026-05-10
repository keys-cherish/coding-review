"""
重构建议生成器。

设计
----
把一次扫描已经产生的多种"症状"聚合成**项目级**的重构任务清单，并按
优先级排序。每条建议包括：

- id: 稳定 key，便于前端去重/收藏
- title: 一行可操作的建议
- rationale: 为什么要做（来自哪些指标）
- targets: 相关文件/函数
- effort: 预计工作量（low / medium / high）
- impact: 预计收益（low / medium / high）
- priority: 综合得分（0~100），impact 高 / effort 低 → 高优先级
- category: 建议类别（method_decomp / class_split / dep_cycle / layer / dup / arg_object）

数据源
------
- ComplexityMetric：函数级 cyclomatic / cognitive / lines / parameters
- Issue（category=smell）：上帝类 / 胖接口 / 上帝方法 / 长参数
- Duplication：重复代码块
- DependencyGraph / find_cycles：循环依赖
- detect_layer_violations：分层违规

返回 Python 结构（dataclass → dict），router 直接 JSON 化即可。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engines.architecture.cycle_detector import detect_cycles
from backend.engines.architecture.dependency_graph import (
    DependencyGraph,
    build_dependency_graph,
)
from backend.engines.architecture.layer_violation import detect_layer_violations
from backend.engines.parser import ParsedFile
from backend.models import (
    ComplexityMetric,
    Duplication,
    Issue,
    ScanTask,
    SourceFile,
)


# ---------- 评分规则 ----------

_EFFORT_SCORE = {"low": 1, "medium": 2, "high": 3}
_IMPACT_SCORE = {"low": 1, "medium": 2, "high": 3}


@dataclass
class Suggestion:
    id: str
    category: str
    title: str
    rationale: str
    targets: list[str] = field(default_factory=list)
    effort: str = "medium"
    impact: str = "medium"
    priority: int = 0
    metrics: dict = field(default_factory=dict)

    def compute_priority(self) -> None:
        """impact / effort 的综合：impact 越高、effort 越低优先级越高。"""
        i = _IMPACT_SCORE.get(self.impact, 2)
        e = _EFFORT_SCORE.get(self.effort, 2)
        # 映射到 0~100，impact 3 / effort 1 得满分 100，反之约 11
        self.priority = int(round((i / e) * 33 + 1))


# ---------- 单项生成器 ----------

def _sid(*parts: str) -> str:
    """稳定 id：对输入做 md5 前 8 位。"""
    raw = "|".join(parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]


def _from_complex_functions(metrics: list[ComplexityMetric], files: dict[int, str]) -> list[Suggestion]:
    """按圈复杂度/认知复杂度挑 Top 10。"""
    hot = [m for m in metrics if m.cyclomatic >= 15 or m.cognitive >= 20 or m.lines >= 80]
    hot.sort(key=lambda m: (m.cyclomatic + m.cognitive, m.lines), reverse=True)
    out: list[Suggestion] = []
    for m in hot[:10]:
        fname = files.get(m.source_file_id, f"#file_{m.source_file_id}")
        sug = Suggestion(
            id=_sid("method_decomp", fname, m.function_name, str(m.start_line)),
            category="method_decomp",
            title=f"拆分复杂方法 {m.function_name}",
            rationale=(
                f"圈复杂度 {m.cyclomatic} / 认知复杂度 {m.cognitive} / {m.lines} 行"
                f"，建议用 Extract Method 或策略模式拆解"
            ),
            targets=[f"{fname}:{m.start_line}"],
            effort="medium",
            impact="high" if m.cyclomatic >= 20 else "medium",
            metrics={
                "cyclomatic": m.cyclomatic,
                "cognitive": m.cognitive,
                "lines": m.lines,
                "parameters": m.parameters,
            },
        )
        sug.compute_priority()
        out.append(sug)
    return out


def _from_smell_issues(issues: list[Issue], files: dict[int, str]) -> list[Suggestion]:
    out: list[Suggestion] = []
    for iss in issues:
        fname = files.get(iss.source_file_id, f"#file_{iss.source_file_id}")
        code = iss.rule_code
        if code in ("PY-SM001", "JAVA-SM001"):
            cat, title, impact, effort = (
                "class_split",
                f"拆分上帝类：{fname}",
                "high",
                "high",
            )
        elif code in ("PY-SM002", "JAVA-SM002"):
            cat, title, impact, effort = (
                "method_decomp",
                f"拆分上帝方法：{fname}:{iss.line}",
                "medium",
                "medium",
            )
        elif code == "JAVA-SM003":
            cat, title, impact, effort = (
                "interface_split",
                f"按 ISP 拆分胖接口：{fname}",
                "high",
                "medium",
            )
        elif code in ("PY-SM003", "JAVA-SM004"):
            cat, title, impact, effort = (
                "arg_object",
                f"引入参数对象：{fname}:{iss.line}",
                "medium",
                "low",
            )
        else:
            continue

        sug = Suggestion(
            id=_sid("smell", code, fname, str(iss.line)),
            category=cat,
            title=title,
            rationale=iss.message + (f"。建议：{iss.suggestion}" if iss.suggestion else ""),
            targets=[f"{fname}:{iss.line}"],
            effort=effort,
            impact=impact,
        )
        sug.compute_priority()
        out.append(sug)
    return out


def _from_cycles(graph: DependencyGraph) -> list[Suggestion]:
    cycles = detect_cycles(graph)
    out: list[Suggestion] = []
    for i, cyc in enumerate(cycles[:5]):
        modules = cyc.shortest_cycle or cyc.modules
        files = [graph.nodes[m].file_path for m in modules if m in graph.nodes]
        sug = Suggestion(
            id=_sid("cycle", *modules),
            category="dep_cycle",
            title=f"打破循环依赖 #{i + 1}（{cyc.size} 个模块，{cyc.severity}）",
            rationale=(
                cyc.description
                + "。可通过引入接口反转依赖（DIP）或抽取共享模块来切断环。"
            ),
            targets=files,
            effort="high",
            impact="high" if cyc.severity in ("critical", "high") else "medium",
            metrics={"size": cyc.size, "severity": cyc.severity},
        )
        sug.compute_priority()
        out.append(sug)
    return out


def _from_layer_violations(graph: DependencyGraph) -> list[Suggestion]:
    payload = detect_layer_violations(graph)
    groups: dict[tuple[str, str], list[dict]] = {}
    for v in payload["violations"]:
        key = (v["src_layer"], v["dst_layer"])
        groups.setdefault(key, []).append(v)

    out: list[Suggestion] = []
    for (sl, dl), items in groups.items():
        sample = [f"{v['src_file']} → {v['dst_file']}" for v in items[:3]]
        sug = Suggestion(
            id=_sid("layer", sl, dl),
            category="layer",
            title=f"修正 {sl} → {dl} 的跨层依赖（{len(items)} 处）",
            rationale=(
                f"发现 {len(items)} 处 {sl} 直接依赖 {dl}；"
                + items[0]["reason"]
                + "。建议下沉公共依赖 / 引入中间层 / 反转依赖。"
            ),
            targets=[v["src_file"] for v in items[:5]],
            effort="medium",
            impact="high" if any(v["severity"] == "error" for v in items) else "medium",
            metrics={"count": len(items), "examples": sample},
        )
        sug.compute_priority()
        out.append(sug)
    return out


def _from_duplications(dups: list[Duplication]) -> list[Suggestion]:
    import json
    heavy = [d for d in dups if d.occurrences >= 2 and d.line_length >= 10]
    heavy.sort(key=lambda d: (d.line_length * d.occurrences), reverse=True)
    out: list[Suggestion] = []
    for d in heavy[:8]:
        try:
            occs = json.loads(d.occurrences_json) or []
        except Exception:
            occs = []
        targets = [f"{o.get('file', '?')}:{o.get('start_line', '?')}" for o in occs[:5]]
        sug = Suggestion(
            id=_sid("dup", d.fingerprint),
            category="dup",
            title=f"抽取 {d.occurrences} 处重复代码（约 {d.line_length} 行）",
            rationale=(
                f"检测方式 {d.detection_method}；重复代码块出现 {d.occurrences} 次，"
                "建议抽取为公共函数或基类。"
            ),
            targets=targets,
            effort="low" if d.line_length < 20 else "medium",
            impact="medium",
            metrics={"token_length": d.token_length, "line_length": d.line_length},
        )
        sug.compute_priority()
        out.append(sug)
    return out


# ---------- 入口 ----------

async def build_suggestions(
    scan_id: int,
    db: AsyncSession,
    parsed_files: list[ParsedFile] | None = None,
) -> dict:
    """聚合生成重构建议。

    parsed_files 可选：若调用方已经解析过（如 visualization 复用），可直接传入，
    避免重复解析。未提供时函数自行加载。
    """
    # scan 存在性 & source_file id → relative_path 索引
    scan = await db.get(ScanTask, scan_id)
    if scan is None:
        raise LookupError(f"扫描任务 {scan_id} 不存在")

    sf_rows = (
        await db.execute(select(SourceFile).where(SourceFile.version_id == scan.version_id))
    ).scalars().all()
    file_by_id = {sf.id: sf.relative_path for sf in sf_rows}

    # 数据源 1：复杂度指标
    metrics = (
        await db.execute(
            select(ComplexityMetric).where(
                ComplexityMetric.source_file_id.in_(file_by_id.keys())
            )
        )
    ).scalars().all()

    # 数据源 2：smell 类 issues
    smell_issues = (
        await db.execute(
            select(Issue).where(
                Issue.scan_task_id == scan_id,
                Issue.category == "smell",
            )
        )
    ).scalars().all()

    # 数据源 3：重复代码
    dups = (
        await db.execute(select(Duplication).where(Duplication.scan_task_id == scan_id))
    ).scalars().all()

    # 数据源 4：依赖图 / 循环 / 分层违规
    cycle_suggestions: list[Suggestion] = []
    layer_suggestions: list[Suggestion] = []
    if parsed_files:
        graph = build_dependency_graph(parsed_files)
        cycle_suggestions = _from_cycles(graph)
        layer_suggestions = _from_layer_violations(graph)

    suggestions: list[Suggestion] = []
    suggestions += _from_complex_functions(metrics, file_by_id)
    suggestions += _from_smell_issues(smell_issues, file_by_id)
    suggestions += _from_duplications(dups)
    suggestions += cycle_suggestions
    suggestions += layer_suggestions

    # 去重：同 id 保留优先级高的
    by_id: dict[str, Suggestion] = {}
    for s in suggestions:
        prev = by_id.get(s.id)
        if prev is None or s.priority > prev.priority:
            by_id[s.id] = s

    final = sorted(by_id.values(), key=lambda s: s.priority, reverse=True)

    # 统计
    by_cat: dict[str, int] = {}
    for s in final:
        by_cat[s.category] = by_cat.get(s.category, 0) + 1

    return {
        "total": len(final),
        "by_category": by_cat,
        "suggestions": [asdict(s) for s in final],
    }


__all__ = ["Suggestion", "build_suggestions"]
