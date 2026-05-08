"""
内置规则入库脚本。

启动时自动执行，将代码中定义的规则元数据同步到数据库。
"""
from __future__ import annotations

from backend.database import get_sync_session
from backend.engines.rules.registry import rule_registry
from backend.models import Rule
from backend.utils import logger


def seed_builtin_rules() -> None:
    """将注册的内置规则同步到 rules 表。"""
    rules = rule_registry.all_rules()
    if not rules:
        logger.warning("规则注册表为空，跳过 seed")
        return

    with get_sync_session() as session:
        existing = {r.code: r for r in session.query(Rule).all()}
        created = updated = 0
        for rule_obj in rules:
            row = existing.get(rule_obj.code)
            if row is None:
                session.add(Rule(
                    code=rule_obj.code,
                    language=rule_obj.language,
                    category=rule_obj.category,
                    name=rule_obj.name,
                    description=rule_obj.description,
                    severity=rule_obj.severity,
                    enabled=True,
                ))
                created += 1
            else:
                row.name = rule_obj.name
                row.description = rule_obj.description
                row.severity = rule_obj.severity
                row.category = rule_obj.category
                updated += 1
        logger.info(f"内置规则同步完成：新增 {created}，更新 {updated}")


if __name__ == "__main__":
    seed_builtin_rules()
