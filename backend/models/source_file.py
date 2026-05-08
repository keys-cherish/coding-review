"""源文件（SourceFile）模型。"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.complexity_metric import ComplexityMetric
    from backend.models.issue import Issue
    from backend.models.version import Version


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("versions.id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(String(500), index=True)
    language: Mapped[str] = mapped_column(String(20))
    lines_of_code: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    file_hash: Mapped[str] = mapped_column(String(64))
    health_score: Mapped[float] = mapped_column(Float, default=100.0)

    version: Mapped["Version"] = relationship(back_populates="source_files")
    issues: Mapped[List["Issue"]] = relationship(
        back_populates="source_file", cascade="all, delete-orphan"
    )
    complexity_metrics: Mapped[List["ComplexityMetric"]] = relationship(
        back_populates="source_file", cascade="all, delete-orphan"
    )
