"""扫描任务（ScanTask）模型。"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.duplication import Duplication
    from backend.models.issue import Issue
    from backend.models.report import Report
    from backend.models.version import Version


class ScanTaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ScanTask(Base):
    __tablename__ = "scan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=ScanTaskStatus.PENDING, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_file: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)

    duplication_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_complexity: Mapped[float] = mapped_column(Float, default=0.0)
    max_complexity: Mapped[int] = mapped_column(Integer, default=0)

    spec_score: Mapped[float] = mapped_column(Float, default=0.0)
    dup_score: Mapped[float] = mapped_column(Float, default=0.0)
    complexity_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(2), default="D")

    error_msg: Mapped[str | None] = mapped_column(Text)

    version: Mapped["Version"] = relationship(back_populates="scan_tasks")
    issues: Mapped[List["Issue"]] = relationship(
        back_populates="scan_task", cascade="all, delete-orphan"
    )
    duplications: Mapped[List["Duplication"]] = relationship(
        back_populates="scan_task", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        back_populates="scan_task", cascade="all, delete-orphan"
    )
