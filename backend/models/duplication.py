"""重复代码块（Duplication）模型。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.scan_task import ScanTask


class Duplication(Base):
    __tablename__ = "duplications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scan_task_id: Mapped[int] = mapped_column(ForeignKey("scan_tasks.id", ondelete="CASCADE"))
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    token_length: Mapped[int] = mapped_column(Integer)
    line_length: Mapped[int] = mapped_column(Integer, default=0)
    occurrences: Mapped[int] = mapped_column(Integer, default=2)
    detection_method: Mapped[str] = mapped_column(String(20), default="token")
    occurrences_json: Mapped[str] = mapped_column(Text)

    scan_task: Mapped["ScanTask"] = relationship(back_populates="duplications")
