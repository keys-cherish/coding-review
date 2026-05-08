"""
数据库初始化脚本。

- 创建所有表
- 写入内置规则
"""
from __future__ import annotations

from backend.database import init_database
from backend.utils import logger


def main() -> None:
    logger.info("正在初始化数据库...")
    init_database()
    logger.info("数据库表创建完成")

    from scripts.seed_rules import seed_builtin_rules
    seed_builtin_rules()


if __name__ == "__main__":
    main()
