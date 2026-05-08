"""
规则管理路由：列出 / 启停。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.engines.rules import rule_registry
from backend.models import Rule
from backend.schemas import RuleOut, RuleToggle

router = APIRouter()


@router.get("", response_model=list[RuleOut], summary="规则列表")
async def list_rules(
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[RuleOut]:
    stmt = select(Rule).order_by(Rule.language, Rule.code)
    if language:
        stmt = stmt.where(Rule.language == language)
    result = await db.execute(stmt)
    return [RuleOut.model_validate(r) for r in result.scalars().all()]


@router.put("/{code}/toggle", response_model=RuleOut, summary="启用/禁用规则")
async def toggle_rule(
    code: str,
    payload: RuleToggle,
    db: AsyncSession = Depends(get_db),
) -> RuleOut:
    result = await db.execute(select(Rule).where(Rule.code == code))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.enabled = payload.enabled
    # 同步内存注册表
    if payload.enabled:
        rule_registry.enable(code)
    else:
        rule_registry.disable(code)
    await db.commit()
    return RuleOut.model_validate(rule)


@router.get("/stats", summary="规则统计")
async def rule_stats() -> dict:
    return rule_registry.stats()
