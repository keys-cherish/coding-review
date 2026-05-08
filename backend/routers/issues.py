"""
问题清单与详情路由。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import ComplexityMetric, Duplication, Issue, SourceFile
from backend.schemas import (
    ComplexityOut,
    DuplicationOut,
    IssueOut,
    IssueWithFile,
)

router = APIRouter()


@router.get("/scan/{scan_id}", response_model=list[IssueWithFile], summary="扫描结果的问题清单")
async def list_issues_of_scan(
    scan_id: int,
    severity: str | None = None,
    rule_code: str | None = None,
    limit: int = 500,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[IssueWithFile]:
    stmt = (
        select(Issue, SourceFile.relative_path)
        .join(SourceFile, SourceFile.id == Issue.source_file_id)
        .where(Issue.scan_task_id == scan_id)
        .order_by(Issue.severity.desc(), Issue.line.asc())
    )
    if severity:
        stmt = stmt.where(Issue.severity == severity)
    if rule_code:
        stmt = stmt.where(Issue.rule_code == rule_code)
    stmt = stmt.limit(limit).offset(offset)

    rows = (await db.execute(stmt)).all()
    out: list[IssueWithFile] = []
    for issue, rel_path in rows:
        out.append(IssueWithFile(
            id=issue.id,
            scan_task_id=issue.scan_task_id,
            source_file_id=issue.source_file_id,
            rule_code=issue.rule_code,
            category=issue.category,
            severity=issue.severity,
            line=issue.line,
            column=issue.column,
            end_line=issue.end_line,
            message=issue.message,
            code_snippet=issue.code_snippet,
            suggestion=issue.suggestion,
            file_path=rel_path,
        ))
    return out


@router.get("/scan/{scan_id}/summary", summary="问题分布概览")
async def issue_summary(scan_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """返回按严重度/规则/文件的统计。"""
    by_severity_q = await db.execute(
        select(Issue.severity, func.count(Issue.id))
        .where(Issue.scan_task_id == scan_id)
        .group_by(Issue.severity)
    )
    by_severity = {sev: cnt for sev, cnt in by_severity_q.all()}

    by_category_q = await db.execute(
        select(Issue.category, func.count(Issue.id))
        .where(Issue.scan_task_id == scan_id)
        .group_by(Issue.category)
    )
    by_category = {cat: cnt for cat, cnt in by_category_q.all()}

    by_rule_q = await db.execute(
        select(Issue.rule_code, func.count(Issue.id))
        .where(Issue.scan_task_id == scan_id)
        .group_by(Issue.rule_code)
        .order_by(desc(func.count(Issue.id)))
        .limit(20)
    )
    top_rules = [{"rule_code": rc, "count": cnt} for rc, cnt in by_rule_q.all()]

    file_q = await db.execute(
        select(SourceFile.relative_path, SourceFile.health_score, func.count(Issue.id))
        .join(Issue, Issue.source_file_id == SourceFile.id)
        .where(Issue.scan_task_id == scan_id)
        .group_by(SourceFile.id)
        .order_by(desc(func.count(Issue.id)))
        .limit(20)
    )
    top_files = [
        {"path": p, "health": h, "issues": cnt}
        for p, h, cnt in file_q.all()
    ]

    return {
        "by_severity": by_severity,
        "by_category": by_category,
        "top_rules": top_rules,
        "top_files": top_files,
    }


@router.get(
    "/scan/{scan_id}/complexity",
    response_model=list[ComplexityOut],
    summary="复杂度排行榜",
)
async def list_complexity(
    scan_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ComplexityOut]:
    stmt = (
        select(ComplexityMetric)
        .join(SourceFile, SourceFile.id == ComplexityMetric.source_file_id)
        .join(SourceFile.version)
        .join(SourceFile.version.scan_tasks if False else SourceFile.version)  # noqa: B015
        .where(SourceFile.version.has())  # 仅占位
    )
    # 用更简单的方法：通过 scan_id -> version_id 反查
    from backend.models import ScanTask

    task = await db.get(ScanTask, scan_id)
    if task is None:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    result = await db.execute(
        select(ComplexityMetric)
        .join(SourceFile, SourceFile.id == ComplexityMetric.source_file_id)
        .where(SourceFile.version_id == task.version_id)
        .order_by(desc(ComplexityMetric.cyclomatic))
        .limit(limit)
    )
    return [ComplexityOut.model_validate(m) for m in result.scalars().all()]


@router.get(
    "/scan/{scan_id}/duplications",
    response_model=list[DuplicationOut],
    summary="重复代码块清单",
)
async def list_duplications(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[DuplicationOut]:
    result = await db.execute(
        select(Duplication)
        .where(Duplication.scan_task_id == scan_id)
        .order_by(desc(Duplication.line_length))
    )
    return [DuplicationOut.model_validate(d) for d in result.scalars().all()]


@router.get("/{issue_id}", response_model=IssueOut, summary="问题详情")
async def get_issue(issue_id: int, db: AsyncSession = Depends(get_db)) -> IssueOut:
    issue = await db.get(Issue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="问题不存在")
    return IssueOut.model_validate(issue)
