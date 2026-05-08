"""项目版本（Version）模型。"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.project import Project
    from backend.models.scan_task import ScanTask
    from backend.models.source_file import SourceFile


class Version(Base):
    __tablename__ = "versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    version_tag: Mapped[str] = mapped_column(String(50), default="v1.0")
    upload_path: Mapped[str] = mapped_column(String(500))
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    project: Mapped["Project"] = relationship(back_populates="versions")
    source_files: Mapped[List["SourceFile"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    scan_tasks: Mapped[List["ScanTask"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
