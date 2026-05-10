"""
数据库初始化脚本。

- 创建所有表
- 触发规则模块导入
- 写入内置规则
"""
from __future__ import annotations

from backend.database import init_database
from backend.engines.rules.registry import discover_rules
from backend.utils import logger


def main() -> None:
    logger.info("正在初始化数据库...")
    init_database()
    logger.info("数据库表创建完成")

    n = discover_rules()
    logger.info(f"已发现 {n} 个规则模块")

    from scripts.seed_rules import seed_builtin_rules
    seed_builtin_rules()


if __name__ == "__main__":
    main()
