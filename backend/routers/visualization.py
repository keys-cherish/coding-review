"""
架构可视化路由。

提供依赖图、调用图、火焰图、热力图、雷达、架构识别、UML 等可视化所需数据。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.engines.architecture import (
    build_dependency_graph,
    compute_arch_radar,
    extract_uml_classes,
    recognize_architecture,
    render_mermaid_class_diagram,
    render_plantuml_class_diagram,
)
from backend.engines.architecture.layer_violation import detect_layer_violations
from backend.models import Issue, SourceFile
from backend.services.visualization_service import (
    build_call_graph_payload,
    build_dependency_graph_payload,
    build_sunburst_payload,
    build_treemap_payload,
    ensure_parsed,
    find_previous_scan,
    load_context,
)

router = APIRouter()


async def _prepare(scan_id: int, db: AsyncSession):
    try:
        ctx = await load_context(scan_id, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    parsed = await ensure_parsed(ctx)
    return ctx, parsed


@router.get("/{scan_id}/dependency-graph", summary="文件/模块级依赖图")
async def dependency_graph(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    _ctx, parsed = await _prepare(scan_id, db)
    return build_dependency_graph_payload(parsed)


@router.get("/{scan_id}/call-graph", summary="函数调用图")
async def call_graph(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    ctx, parsed = await _prepare(scan_id, db)
    return build_call_graph_payload(parsed, ctx.complexity_by_file)


@router.get("/{scan_id}/flame", summary="旭日 / 火焰图 hierarchy")
async def flame(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    ctx, parsed = await _prepare(scan_id, db)
    return build_sunburst_payload(parsed, ctx.complexity_by_file)


@router.get("/{scan_id}/treemap", summary="热力 Treemap")
async def treemap(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    ctx, parsed = await _prepare(scan_id, db)

    # 每个文件的 issue 计数
    rows = (await db.execute(
        select(SourceFile.relative_path, func.count(Issue.id))
        .join(Issue, Issue.source_file_id == SourceFile.id)
        .where(Issue.scan_task_id == scan_id)
        .group_by(SourceFile.id)
    )).all()
    issues_per_file = {p: int(c) for p, c in rows}

    return build_treemap_payload(parsed, ctx.complexity_by_file, issues_per_file)


@router.get("/{scan_id}/radar", summary="六维架构雷达")
async def radar(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    ctx, parsed = await _prepare(scan_id, db)
    graph = build_dependency_graph(parsed)

    total_loc = sum(pf.lines_of_code for pf in parsed) or 1
    radar_payload = compute_arch_radar(
        graph,
        total_issues=ctx.scan.total_issues,
        total_loc=total_loc,
        duplication_rate=ctx.scan.duplication_rate or 0.0,
    )

    prev_scan = await find_previous_scan(db, ctx.scan)
    previous = None
    if prev_scan is not None:
        try:
            prev_ctx = await load_context(prev_scan.id, db)
            prev_parsed = await ensure_parsed(prev_ctx)
            prev_graph = build_dependency_graph(prev_parsed)
            prev_loc = sum(pf.lines_of_code for pf in prev_parsed) or 1
            previous = compute_arch_radar(
                prev_graph,
                total_issues=prev_scan.total_issues,
                total_loc=prev_loc,
                duplication_rate=prev_scan.duplication_rate or 0.0,
            )
            previous["scan_id"] = prev_scan.id
        except Exception:
            previous = None

    return {
        **radar_payload,
        "previous": previous,
    }


@router.get("/{scan_id}/architecture", summary="架构模式识别")
async def architecture(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    _ctx, parsed = await _prepare(scan_id, db)
    graph = build_dependency_graph(parsed)
    result = recognize_architecture(graph)
    # 顺带附上分层违规摘要，方便前端在架构页一站式查看
    result["layer_violations"] = detect_layer_violations(graph)
    return result


@router.get("/{scan_id}/layer-violations", summary="分层违规检测")
async def layer_violations(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    _ctx, parsed = await _prepare(scan_id, db)
    graph = build_dependency_graph(parsed)
    return detect_layer_violations(graph)


@router.get("/{scan_id}/refactor", summary="重构建议")
async def refactor_suggestions(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    from backend.services.refactor_service import build_suggestions
    _ctx, parsed = await _prepare(scan_id, db)
    return await build_suggestions(scan_id, db, parsed_files=parsed)


@router.get("/{scan_id}/uml", summary="UML 类图")
async def uml(
    scan_id: int,
    type: str = Query("class", pattern="^(class|sequence|component)$"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _ctx, parsed = await _prepare(scan_id, db)
    if type != "class":
        return {
            "mermaid": f"%% {type} 图暂未实现",
            "plantuml": f"@startuml\nnote as N1\n{type} diagram TBD\nend note\n@enduml",
            "classes": [],
            "type": type,
        }
    classes = extract_uml_classes(parsed)
    mermaid = render_mermaid_class_diagram(classes)
    plantuml = render_plantuml_class_diagram(classes)
    return {
        "mermaid": mermaid,
        "plantuml": plantuml,
        "classes": [c.to_dict() for c in classes],
        "type": type,
    }


@router.get("", summary="扫描列表（供可视化页选择）")
async def list_scans_for_viz(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """列出所有已完成扫描，按时间降序，带 project 名称和版本 tag。"""
    from backend.models import Project, ScanTask, Version
    stmt = (
        select(ScanTask, Version, Project)
        .join(Version, Version.id == ScanTask.version_id)
        .join(Project, Project.id == Version.project_id)
        .order_by(ScanTask.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": t.id,
            "status": t.status,
            "grade": t.grade,
            "overall_score": t.overall_score,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "project_id": p.id,
            "project_name": p.name,
            "version_id": v.id,
            "version_tag": v.version_tag,
            "total_issues": t.total_issues,
            "duplication_rate": t.duplication_rate,
        }
        for t, v, p in rows
    ]
