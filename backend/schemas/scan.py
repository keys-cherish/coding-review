"""
扫描任务相关 Pydantic 模型。
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    status: str
    progress: float
    current_file: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    total_issues: int
    error_count: int
    warning_count: int
    info_count: int

    duplication_rate: float
    avg_complexity: float
    max_complexity: int

    spec_score: float
    dup_score: float
    complexity_score: float
    overall_score: float
    grade: str

    error_msg: str | None = None


class ScanProgressEvent(BaseModel):
    """WebSocket 推送事件。"""
    scan_id: int
    status: str
    progress: float
    current_file: str | None = None
    issues_found: int = 0
    message: str | None = None
