"""
Python 代码坏味道规则（SMELL-*）。

底层实现复用 `engines.smells` 中的跨语言检测器。
顶层避免 import `engines.smells`（会与规则 discovery 形成循环），
改在 check() 中延迟 import。
"""
from __future__ import annotations

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class PyGodClassRule(Rule):
    code = "PY-SM001"
    language = "python"
    category = "smell"
    severity = "warning"
    name = "上帝类"
    description = "单一类承担过多职责（方法/行数/字段数超过阈值）"
    suggestion_template = "按单一职责原则拆分为更小的类"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_god_classes
        out = detect_god_classes(parsed)
        for i in out:
            i.rule_code = self.code
        return out


@register
class PyGodMethodRule(Rule):
    code = "PY-SM002"
    language = "python"
    category = "smell"
    severity = "warning"
    name = "上帝方法"
    description = "单函数过长或圈复杂度过高"
    suggestion_template = "Extract Method 拆分子步骤"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_god_methods
        out = detect_god_methods(parsed)
        for i in out:
            i.rule_code = self.code
        return out


@register
class PyLongParamListRule(Rule):
    code = "PY-SM003"
    language = "python"
    category = "smell"
    severity = "info"
    name = "过长参数列表"
    description = "参数数量超过 5"
    suggestion_template = "引入参数对象或 dataclass"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_long_parameter_lists
        out = detect_long_parameter_lists(parsed)
        for i in out:
            i.rule_code = self.code
        return out

