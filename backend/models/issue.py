"""问题记录（Issue）模型。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.scan_task import ScanTask
    from backend.models.source_file import SourceFile


class Severity:
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        Index("ix_issues_scan_severity", "scan_task_id", "severity"),
        Index("ix_issues_file_line", "source_file_id", "line"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_task_id: Mapped[int] = mapped_column(ForeignKey("scan_tasks.id", ondelete="CASCADE"))
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id", ondelete="CASCADE"))
    rule_code: Mapped[str] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(10))
    line: Mapped[int] = mapped_column(Integer)
    column: Mapped[int] = mapped_column(Integer, default=0)
    end_line: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text)
    code_snippet: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)

    scan_task: Mapped["ScanTask"] = relationship(back_populates="issues")
    source_file: Mapped["SourceFile"] = relationship(back_populates="issues")
