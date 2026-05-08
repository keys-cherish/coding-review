"""
规则注册中心。

提供：
- @register 装饰器：声明式注册规则类
- RuleRegistry：单例，管理所有规则的启用/查询
- discover_rules()：触发所有内置规则模块的导入，让装饰器执行
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Type

from backend.engines.rules.base import Rule


class RuleRegistry:
    """规则注册表（单例模式）。"""

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule_cls: Type[Rule]) -> Type[Rule]:
        """注册一个规则类（装饰器）。"""
        if not rule_cls.code:
            raise ValueError(f"规则 {rule_cls.__name__} 未设置 code")
        instance = rule_cls()
        if instance.code in self._rules:
            existing = self._rules[instance.code]
            raise ValueError(
                f"规则 code 冲突: {instance.code} 已被 "
                f"{type(existing).__name__} 注册，又被 {rule_cls.__name__} 重复"
            )
        self._rules[instance.code] = instance
        return rule_cls

    def all_rules(self) -> list[Rule]:
        return list(self._rules.values())

    def by_language(self, language: str) -> list[Rule]:
        return [r for r in self._rules.values() if r.language == language and r.enabled]

    def by_code(self, code: str) -> Rule | None:
        return self._rules.get(code)

    def enable(self, code: str) -> bool:
        if code in self._rules:
            self._rules[code].enabled = True
            return True
        return False

    def disable(self, code: str) -> bool:
        if code in self._rules:
            self._rules[code].enabled = False
            return True
        return False

    def stats(self) -> dict:
        from collections import Counter
        per_lang = Counter(r.language for r in self._rules.values())
        per_severity = Counter(r.severity for r in self._rules.values())
        return {
            "total": len(self._rules),
            "by_language": dict(per_lang),
            "by_severity": dict(per_severity),
        }


rule_registry = RuleRegistry()


def register(rule_cls: Type[Rule]) -> Type[Rule]:
    """简便装饰器。"""
    return rule_registry.register(rule_cls)


def discover_rules() -> int:
    """递归 import 所有内置规则模块，触发装饰器注册。"""
    import backend.engines.rules.python as py_pkg
    import backend.engines.rules.java as java_pkg

    count = 0
    for pkg in (py_pkg, java_pkg):
        for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg.__name__}.{modname}")
            count += 1
    return count
