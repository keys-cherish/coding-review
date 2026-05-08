"""
报告生成服务 - 根据 scan_id 收集数据并调用对应渲染器。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import (
    ComplexityMetric,
    Duplication,
    Issue,
    Project,
    ScanTask,
    SourceFile,
    Version,
)
from backend.reports.html_renderer import render_html
from backend.reports.markdown_renderer import render_markdown
from backend.reports.pdf_renderer import render_pdf
from backend.utils import logger


async def collect_report_data(scan_id: int, db: AsyncSession) -> dict:
    """收集生成报告所需的全部数据。"""
    task = await db.get(ScanTask, scan_id)
    if task is None:
        raise ValueError("扫描任务不存在")
    version = await db.get(Version, task.version_id)
    project = await db.get(Project, version.project_id) if version else None

    issues_q = await db.execute(
        select(Issue, SourceFile.relative_path)
        .join(SourceFile, SourceFile.id == Issue.source_file_id)
        .where(Issue.scan_task_id == scan_id)
        .order_by(Issue.severity.desc(), Issue.line)
    )
    issues = []
    file_issue_count: dict[str, int] = {}
    severity_count = {"error": 0, "warning": 0, "info": 0}
    category_count: dict[str, int] = {}
    rule_count: dict[str, int] = {}
    for issue, rel_path in issues_q.all():
        issues.append({
            "rule_code": issue.rule_code,
            "category": issue.category,
            "severity": issue.severity,
            "file_path": rel_path,
            "line": issue.line,
            "message": issue.message,
            "code_snippet": issue.code_snippet,
            "suggestion": issue.suggestion,
        })
        file_issue_count[rel_path] = file_issue_count.get(rel_path, 0) + 1
        severity_count[issue.severity] = severity_count.get(issue.severity, 0) + 1
        category_count[issue.category] = category_count.get(issue.category, 0) + 1
        rule_count[issue.rule_code] = rule_count.get(issue.rule_code, 0) + 1

    cm_q = await db.execute(
        select(ComplexityMetric, SourceFile.relative_path)
        .join(SourceFile, SourceFile.id == ComplexityMetric.source_file_id)
        .where(SourceFile.version_id == task.version_id)
        .order_by(ComplexityMetric.cyclomatic.desc())
        .limit(30)
    )
    complexity = []
    for m, rel_path in cm_q.all():
        complexity.append({
            "function_name": m.function_name,
            "file_path": rel_path,
            "lines": m.lines,
            "cyclomatic": m.cyclomatic,
            "cognitive": m.cognitive,
            "nesting_depth": m.nesting_depth,
            "risk_level": m.risk_level,
            "start_line": m.start_line,
        })

    dup_q = await db.execute(
        select(Duplication)
        .where(Duplication.scan_task_id == scan_id)
        .order_by(Duplication.line_length.desc())
    )
    duplications = []
    for d in dup_q.scalars().all():
        try:
            occs = json.loads(d.occurrences_json)
        except Exception:
            occs = []
        duplications.append({
            "fingerprint": d.fingerprint,
            "method": d.detection_method,
            "line_length": d.line_length,
            "occurrences": occs,
        })

    top_files = sorted(
        [{"path": p, "issues": c} for p, c in file_issue_count.items()],
        key=lambda x: x["issues"],
        reverse=True,
    )[:10]

    summary = _summarize(task, severity_count, len(duplications), len(complexity))

    return {
        "project": {
            "name": project.name if project else "(未知)",
            "language": project.language if project else "",
            "description": project.description if project else "",
        },
        "version": {
            "tag": version.version_tag if version else "",
            "uploaded_at": version.uploaded_at.isoformat() if version else "",
            "total_files": version.total_files if version else 0,
            "total_lines": version.total_lines if version else 0,
        },
        "scan": {
            "id": task.id,
            "started_at": task.started_at.isoformat() if task.started_at else "",
            "finished_at": task.finished_at.isoformat() if task.finished_at else "",
            "duration_sec": (
                int((task.finished_at - task.started_at).total_seconds())
                if task.finished_at and task.started_at else 0
            ),
        },
        "score": {
            "overall": task.overall_score,
            "spec": task.spec_score,
            "duplication": task.dup_score,
            "complexity": task.complexity_score,
            "grade": task.grade,
        },
        "metrics": {
            "total_issues": task.total_issues,
            "error_count": task.error_count,
            "warning_count": task.warning_count,
            "info_count": task.info_count,
            "duplication_rate": task.duplication_rate,
            "avg_complexity": task.avg_complexity,
            "max_complexity": task.max_complexity,
        },
        "summary": summary,
        "severity_count": severity_count,
        "category_count": category_count,
        "top_rules": sorted(
            [{"rule_code": k, "count": v} for k, v in rule_count.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10],
        "top_files": top_files,
        "issues": issues,
        "complexity": complexity,
        "duplications": duplications,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _summarize(task: ScanTask, sev: dict, dup_blocks: int, complex_funcs: int) -> str:
    lines = []
    lines.append(f"综合评分 {task.overall_score:.1f} 分（{task.grade} 级）。")
    lines.append(
        f"共发现 {task.total_issues} 个问题："
        f"严重 {sev.get('error', 0)} 个 / 警告 {sev.get('warning', 0)} 个 / 提示 {sev.get('info', 0)} 个。"
    )
    if dup_blocks > 0:
        lines.append(f"识别出 {dup_blocks} 处重复代码块，重复率 {task.duplication_rate * 100:.1f}%。")
    if complex_funcs > 0:
        lines.append(f"高复杂度函数共 {complex_funcs} 个，最高圈复杂度 {task.max_complexity}。")
    if task.grade in ("A", "B"):
        lines.append("代码质量整体良好，建议继续保持工程规范。")
    elif task.grade == "C":
        lines.append("代码质量中等，建议优先修复 ERROR 与 WARNING 类问题，控制函数复杂度。")
    else:
        lines.append("代码存在较多问题，建议优先处理严重问题、降重复率与控制复杂度。")
    return " ".join(lines)


async def generate_report(scan_id: int, fmt: str, db: AsyncSession) -> Path:
    """生成报告，返回文件路径。"""
    data = await collect_report_data(scan_id, db)
    settings.report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = settings.report_dir / f"scan_{scan_id}_{timestamp}"

    if fmt == "html":
        html = render_html(data)
        out = base.with_suffix(".html")
        out.write_text(html, encoding="utf-8")
        return out
    if fmt == "md":
        md = render_markdown(data)
        out = base.with_suffix(".md")
        out.write_text(md, encoding="utf-8")
        return out
    if fmt == "pdf":
        try:
            return render_pdf(data, base.with_suffix(".pdf"))
        except Exception as e:
            logger.warning(f"PDF 渲染失败，降级为 HTML: {e}")
            html = render_html(data)
            out = base.with_suffix(".html")
            out.write_text(html, encoding="utf-8")
            return out
    raise ValueError(f"不支持的报告格式: {fmt}")
