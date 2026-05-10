"""
Java 代码坏味道规则（SMELL-*）。

底层复用 `engines.smells` 中的跨语言检测器；
顶层避免 import `engines.smells`（会形成循环），改在 check() 中延迟导入。
"""
from __future__ import annotations

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class JavaGodClassRule(Rule):
    code = "JAVA-SM001"
    language = "java"
    category = "smell"
    severity = "warning"
    name = "上帝类"
    description = "单一类承担过多职责"
    suggestion_template = "按单一职责原则拆分"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_god_classes
        out = detect_god_classes(parsed)
        for i in out:
            i.rule_code = self.code
        return out


@register
class JavaGodMethodRule(Rule):
    code = "JAVA-SM002"
    language = "java"
    category = "smell"
    severity = "warning"
    name = "上帝方法"
    description = "单方法过长或圈复杂度过高"
    suggestion_template = "Extract Method"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_god_methods
        out = detect_god_methods(parsed)
        for i in out:
            i.rule_code = self.code
        return out


@register
class JavaFatInterfaceRule(Rule):
    code = "JAVA-SM003"
    language = "java"
    category = "smell"
    severity = "warning"
    name = "胖接口"
    description = "接口方法数超过 15，违反接口隔离原则 (ISP)"
    suggestion_template = "按职责拆分为多个更小的接口"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_fat_interfaces
        out = detect_fat_interfaces(parsed)
        for i in out:
            i.rule_code = self.code
        return out


@register
class JavaLongParamListRule(Rule):
    code = "JAVA-SM004"
    language = "java"
    category = "smell"
    severity = "info"
    name = "过长参数列表"
    description = "参数数量超过 5"
    suggestion_template = "引入参数对象或 Builder 模式"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        from backend.engines.smells import detect_long_parameter_lists
        out = detect_long_parameter_lists(parsed)
        for i in out:
            i.rule_code = self.code
        return out
