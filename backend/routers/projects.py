"""
项目管理路由：CRUD + 列表 + 版本列表。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Project, ScanTask, Version
from backend.schemas import ProjectCreate, ProjectOut, VersionOut

router = APIRouter()


@router.get("", response_model=list[ProjectOut], summary="项目列表")
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[ProjectOut]:
    result = await db.execute(select(Project).order_by(desc(Project.created_at)))
    projects = result.scalars().all()

    out: list[ProjectOut] = []
    for p in projects:
        vc = await db.execute(
            select(func.count(Version.id)).where(Version.project_id == p.id)
        )
        version_count = vc.scalar_one()

        latest = await db.execute(
            select(ScanTask.overall_score, ScanTask.grade)
            .join(Version, Version.id == ScanTask.version_id)
            .where(Version.project_id == p.id, ScanTask.status == "done")
            .order_by(desc(ScanTask.finished_at))
            .limit(1)
        )
        row = latest.first()
        out.append(ProjectOut(
            id=p.id,
            name=p.name,
            description=p.description,
            language=p.language,
            created_at=p.created_at,
            updated_at=p.updated_at,
            version_count=version_count,
            latest_score=row[0] if row else None,
            latest_grade=row[1] if row else None,
        ))
    return out


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, summary="创建项目")
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    if payload.language not in ("python", "java", "multi"):
        raise HTTPException(status_code=400, detail="language 必须是 python/java/multi")
    project = Project(
        name=payload.name,
        description=payload.description,
        language=payload.language,
    )
    db.add(project)
    await db.flush()
    await db.commit()
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut, summary="项目详情")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    p = await db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectOut.model_validate(p)


@router.delete("/{project_id}", status_code=204, summary="删除项目")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)) -> None:
    p = await db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    await db.delete(p)
    await db.commit()


@router.get("/{project_id}/versions", response_model=list[VersionOut], summary="版本列表")
async def list_versions(project_id: int, db: AsyncSession = Depends(get_db)) -> list[VersionOut]:
    result = await db.execute(
        select(Version).where(Version.project_id == project_id).order_by(desc(Version.uploaded_at))
    )
    versions = result.scalars().all()
    return [VersionOut.model_validate(v) for v in versions]
