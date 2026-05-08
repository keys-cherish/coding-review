"""复杂度度量（ComplexityMetric）模型。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.source_file import SourceFile


class ComplexityMetric(Base):
    __tablename__ = "complexity_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id", ondelete="CASCADE"), index=True)
    function_name: Mapped[str] = mapped_column(String(200))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    lines: Mapped[int] = mapped_column(Integer)
    cyclomatic: Mapped[int] = mapped_column(Integer, default=1)
    cognitive: Mapped[int] = mapped_column(Integer, default=0)
    nesting_depth: Mapped[int] = mapped_column(Integer, default=0)
    parameters: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(10), default="low")

    source_file: Mapped["SourceFile"] = relationship(back_populates="complexity_metrics")
