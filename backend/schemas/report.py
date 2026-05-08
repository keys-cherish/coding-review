"""
报告相关 Pydantic 模型。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_task_id: int
    format: str
    file_path: str
    generated_at: datetime


class ReportRequest(BaseModel):
    format: str  # html / pdf / md
