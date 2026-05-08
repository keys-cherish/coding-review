"""
报告路由：生成 / 下载。
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Report, ScanTask
from backend.schemas import ReportOut, ReportRequest
from backend.services.report_service import generate_report

router = APIRouter()


@router.post("/{scan_id}/generate", response_model=ReportOut, summary="生成报告")
async def gen_report(
    scan_id: int,
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
) -> ReportOut:
    fmt = payload.format.lower()
    if fmt not in ("html", "pdf", "md"):
        raise HTTPException(status_code=400, detail="format 必须是 html / pdf / md")

    task = await db.get(ScanTask, scan_id)
    if task is None:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    if task.status != "done":
        raise HTTPException(status_code=400, detail="扫描尚未完成，无法生成报告")

    file_path = await generate_report(scan_id, fmt, db)

    report = Report(scan_task_id=scan_id, format=fmt, file_path=str(file_path))
    db.add(report)
    await db.flush()
    await db.commit()
    return ReportOut.model_validate(report)


@router.get("/{report_id}/download", summary="下载报告")
async def download_report(report_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    p = Path(report.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="报告文件已不存在")

    media_map = {"html": "text/html", "pdf": "application/pdf", "md": "text/markdown"}
    media_type = media_map.get(report.format, "application/octet-stream")
    filename = f"codeguard_report_{report.scan_task_id}.{report.format}"
    return FileResponse(path=p, media_type=media_type, filename=filename)


@router.get("/scan/{scan_id}", response_model=list[ReportOut], summary="某扫描的全部报告")
async def list_reports(scan_id: int, db: AsyncSession = Depends(get_db)) -> list[ReportOut]:
    result = await db.execute(
        select(Report).where(Report.scan_task_id == scan_id).order_by(Report.id.desc())
    )
    return [ReportOut.model_validate(r) for r in result.scalars().all()]


@router.get("/{report_id}/inline", summary="在线查看（仅 HTML/MD）")
async def view_inline(report_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    if report.format not in ("html", "md"):
        raise HTTPException(status_code=400, detail="仅 HTML/MD 支持在线查看")
    p = Path(report.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="报告文件已不存在")
    return FileResponse(p, media_type="text/html" if report.format == "html" else "text/markdown")
