"""
项目相关 Pydantic 模型。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """创建项目请求体。"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: str | None = Field(None, max_length=500)
    language: str = Field(..., description="主语言：python / java / multi")


class ProjectOut(BaseModel):
    """项目响应体。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    language: str
    created_at: datetime
    updated_at: datetime | None = None
    version_count: int | None = None
    latest_score: float | None = None
    latest_grade: str | None = None


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version_tag: str
    total_files: int
    total_lines: int
    uploaded_at: datetime
