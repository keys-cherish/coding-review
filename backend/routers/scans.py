"""
扫描任务路由：上传+创建任务+查询+列表+触发。
"""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal, get_db
from backend.models import Project, ScanTask, Version
from backend.schemas import ScanTaskOut, VersionOut
from backend.services.scan_orchestrator import ScanOrchestrator
from backend.services.upload_service import save_upload
from backend.utils import logger

router = APIRouter()


@router.post(
    "/upload",
    response_model=VersionOut,
    summary="上传 ZIP 代码包并创建版本",
)
async def upload_code(
    project_id: int = Form(...),
    version_tag: str = Form("v1.0"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> VersionOut:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="仅支持 .zip 上传")

    # 落盘到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # 先创建 Version 占位（拿到 id）
    version = Version(
        project_id=project_id,
        version_tag=version_tag,
        upload_path="",
        total_files=0,
        total_lines=0,
    )
    db.add(version)
    await db.flush()

    # 解压到 data/uploads/<project>/<version>/
    dest = save_upload(project_id, version.id, tmp_path)
    version.upload_path = str(dest)
    await db.flush()
    await db.commit()
    await db.refresh(version)

    return VersionOut.model_validate(version)


@router.post(
    "/{version_id}/start",
    response_model=ScanTaskOut,
    summary="为指定版本创建并启动扫描任务",
)
async def start_scan(
    version_id: int,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanTaskOut:
    version = await db.get(Version, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="版本不存在")

    task = ScanTask(version_id=version_id)
    db.add(task)
    await db.flush()
    await db.commit()
    await db.refresh(task)

    # 后台异步执行
    asyncio.create_task(_run_scan_in_background(task.id))

    return ScanTaskOut.model_validate(task)


async def _run_scan_in_background(scan_id: int) -> None:
    """新开会话跑扫描任务。"""
    async with AsyncSessionLocal() as session:
        try:
            orch = ScanOrchestrator()
            await orch.run_scan(scan_id, session)
            await session.commit()
        except Exception as e:
            logger.exception(f"后台扫描 {scan_id} 异常: {e}")
            await session.rollback()


@router.get(
    "/{scan_id}",
    response_model=ScanTaskOut,
    summary="扫描任务详情",
)
async def get_scan(scan_id: int, db: AsyncSession = Depends(get_db)) -> ScanTaskOut:
    task = await db.get(ScanTask, scan_id)
    if task is None:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    return ScanTaskOut.model_validate(task)


@router.get(
    "/version/{version_id}",
    response_model=list[ScanTaskOut],
    summary="某版本的所有扫描任务",
)
async def list_scans_of_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ScanTaskOut]:
    result = await db.execute(
        select(ScanTask)
        .where(ScanTask.version_id == version_id)
        .order_by(desc(ScanTask.created_at))
    )
    return [ScanTaskOut.model_validate(t) for t in result.scalars().all()]
