"""
规则引擎主入口。

负责：
- 让所有内置规则模块在 import 时被加载注册
- 暴露 RuleEngine 类供 ScanOrchestrator 使用
"""
from __future__ import annotations

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import (
    RuleRegistry,
    discover_rules,
    register,
    rule_registry,
)


class RuleEngine:
    """对单文件运行该语言的全部启用规则。"""

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self._registry = registry or rule_registry

    def check_file(self, parsed: ParsedFile) -> list[Issue]:
        """对一个 ParsedFile 跑全部启用规则，返回所有问题。"""
        rules = self._registry.by_language(parsed.language)
        issues: list[Issue] = []
        for rule in rules:
            try:
                issues.extend(rule.check(parsed))
            except Exception as e:  # 单条规则失败不影响其他规则
                from backend.utils import logger
                logger.warning(
                    f"规则 {rule.code} 在 {parsed.file_path} 上执行失败: {type(e).__name__}: {e}"
                )
        return issues


# 启动期一次性发现内置规则
_RULE_LOAD_COUNT = discover_rules()


__all__ = [
    "Issue",
    "Rule",
    "RuleEngine",
    "RuleRegistry",
    "discover_rules",
    "register",
    "rule_registry",
]
