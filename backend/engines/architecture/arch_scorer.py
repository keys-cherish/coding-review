"""
六维架构雷达打分器。

六个维度（0~100 分，越高越好）：
- clarity    架构清晰度：命中典型分层的目录比例 + 顶层目录命名规范
- isolation  分层隔离度：跨层/反向边占比越低越好
- decoupling 模块解耦度：SCC 占比 / 平均 fan-out 越小越好
- cohesion   组件内聚度：簇内边 / 簇间边 的比值
- spec       规范执行力：直接用 RuleEngine 结果换算（1 - issues / loc）
- dedup      重复冗余度：1 - 重复率
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from backend.engines.architecture.dependency_graph import DependencyGraph
from backend.engines.architecture.cycle_detector import detect_cycles


@dataclass
class ArchDimensionScore:
    name: str
    score: float
    detail: str


def _clarity_score(graph: DependencyGraph) -> tuple[float, str]:
    """命中 controller/service/repo/domain/view 的目录越多越清晰。"""
    layer_keys = {"controller", "controllers", "service", "services",
                  "repository", "repositories", "dao", "model", "models",
                  "domain", "view", "views", "usecase", "usecases",
                  "handler", "handlers", "api"}
    hit_dirs = set()
    top_dirs = set()
    for node in graph.nodes.values():
        parts = PurePosixPath(node.file_path).parts
        if parts:
            top_dirs.add(parts[0])
        for p in parts[:-1]:
            if p.lower() in layer_keys:
                hit_dirs.add(p.lower())
    # 有 1 个命中就 40 分，有 4 个拉满
    base = min(100.0, 40 + 15 * len(hit_dirs))
    if not top_dirs:
        return 0.0, "未找到源码目录"
    # 如果文件全堆在根目录：扣分
    if len(top_dirs) == 1 and not hit_dirs:
        base = 50.0
    return base, f"命中分层目录 {sorted(hit_dirs) or '无'}"


def _build_file_to_layer(graph: DependencyGraph) -> dict[str, str]:
    """文件路径 → 层标签，用于跨层统计。"""
    tags = {
        "controller": ["controller", "controllers", "handler", "handlers", "api", "routes", "router", "routers", "views", "web"],
        "service":    ["service", "services", "biz", "usecase", "usecases", "application"],
        "repository": ["repository", "repositories", "repo", "dao", "mapper", "persistence"],
        "domain":     ["domain", "model", "models", "entity", "entities"],
        "infra":      ["infra", "infrastructure", "adapter", "adapters"],
    }
    mapping: dict[str, str] = {}
    for node in graph.nodes.values():
        parts = [p.lower() for p in PurePosixPath(node.file_path).parts]
        for layer, keys in tags.items():
            if any(p in keys for p in parts):
                mapping[node.file_path] = layer
                break
    return mapping


_LAYER_ORDER = {"controller": 0, "service": 1, "domain": 2, "repository": 3, "infra": 4}


def _isolation_score(graph: DependencyGraph) -> tuple[float, str]:
    """反向跨层边占比越低越好。"""
    file_layer = _build_file_to_layer(graph)
    if not graph.edges:
        return 85.0, "暂无依赖边，默认给高分"
    reverse = 0
    cross = 0
    total = 0
    for (src, dst) in graph.edges.keys():
        s_file = graph.nodes[src].file_path if src in graph.nodes else None
        d_file = graph.nodes[dst].file_path if dst in graph.nodes else None
        sl = file_layer.get(s_file or "")
        dl = file_layer.get(d_file or "")
        if not sl or not dl:
            continue
        total += 1
        if sl != dl:
            cross += 1
        if sl in _LAYER_ORDER and dl in _LAYER_ORDER and _LAYER_ORDER[sl] > _LAYER_ORDER[dl]:
            reverse += 1
    if total == 0:
        return 80.0, "未能识别层级，依赖无法判定"
    rev_ratio = reverse / total
    # 反向依赖越少分越高
    score = max(0.0, 100.0 - rev_ratio * 120.0)
    return score, f"反向依赖 {reverse}/{total} ({rev_ratio:.0%})"


def _decoupling_score(graph: DependencyGraph) -> tuple[float, str]:
    cycles = detect_cycles(graph)
    n = len(graph.nodes) or 1
    scc_mods = sum(c.size for c in cycles if c.size > 1)
    fan_out = sum(len(a) for a in graph.adjacency.values()) / n
    # fan_out > 8 或 scc 比例 > 0.15 重扣
    score = 100.0
    score -= min(50.0, (scc_mods / n) * 200.0)
    score -= max(0.0, (fan_out - 4) * 5)
    score = max(0.0, score)
    return score, f"循环模块 {scc_mods}/{n}, 平均出度 {fan_out:.2f}"


def _cohesion_score(graph: DependencyGraph) -> tuple[float, str]:
    """以顶层目录为簇：簇内边 / 簇间边 比值越高越内聚。"""
    if not graph.edges:
        return 75.0, "依赖数为 0"
    intra = 0
    inter = 0
    for (src, dst) in graph.edges.keys():
        s_top = PurePosixPath(graph.nodes[src].file_path).parts[:1] if src in graph.nodes else ()
        d_top = PurePosixPath(graph.nodes[dst].file_path).parts[:1] if dst in graph.nodes else ()
        if s_top and d_top:
            if s_top == d_top:
                intra += 1
            else:
                inter += 1
    total = intra + inter
    if total == 0:
        return 70.0, "无跨簇统计"
    ratio = intra / total
    score = 40 + ratio * 60.0
    return score, f"簇内依赖占比 {ratio:.0%}"


def _spec_score(issue_stats: dict) -> tuple[float, str]:
    """issue_stats = {total_issues, total_loc}。"""
    total = issue_stats.get("total_issues", 0)
    loc = max(1, issue_stats.get("total_loc", 1))
    density = total / loc
    score = max(0.0, 100.0 - density * 400.0)
    return score, f"{total} 个问题 / {loc} 行 = 密度 {density:.3f}"


def _dedup_score(dup_rate: float) -> tuple[float, str]:
    """重复率 0.0~1.0。"""
    score = max(0.0, 100.0 - dup_rate * 200.0)
    return score, f"重复率 {dup_rate:.1%}"


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "E"


def compute_arch_radar(
    graph: DependencyGraph,
    *,
    total_issues: int,
    total_loc: int,
    duplication_rate: float,
) -> dict:
    """返回 {dimensions, overall, grade}。"""
    dims = [
        ArchDimensionScore("架构清晰度", *_clarity_score(graph)),
        ArchDimensionScore("分层隔离度", *_isolation_score(graph)),
        ArchDimensionScore("模块解耦度", *_decoupling_score(graph)),
        ArchDimensionScore("组件内聚度", *_cohesion_score(graph)),
        ArchDimensionScore("规范执行力", *_spec_score({"total_issues": total_issues, "total_loc": total_loc})),
        ArchDimensionScore("重复冗余度", *_dedup_score(duplication_rate)),
    ]
    overall = sum(d.score for d in dims) / len(dims)
    return {
        "dimensions": [
            {"name": d.name, "score": round(d.score, 1), "detail": d.detail}
            for d in dims
        ],
        "overall": round(overall, 1),
        "grade": _grade(overall),
    }
