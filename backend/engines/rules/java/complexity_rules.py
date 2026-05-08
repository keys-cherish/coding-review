"""
Java 复杂度规则（JA-X001 圈复杂度）。
"""
from __future__ import annotations

from javalang.tree import (
    BinaryOperation,
    CatchClause,
    DoStatement,
    ForStatement,
    IfStatement,
    MethodDeclaration,
    SwitchStatementCase,
    TernaryExpression,
    WhileStatement,
)

from backend.config import settings
from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

_DECISION = (IfStatement, ForStatement, WhileStatement, DoStatement, CatchClause, SwitchStatementCase, TernaryExpression)


def _java_cyclomatic(method: MethodDeclaration) -> int:
    """对单个 Java 方法计算圈复杂度。"""
    cc = 1
    for path, node in method:
        if isinstance(node, _DECISION):
            cc += 1
        elif isinstance(node, BinaryOperation) and node.operator in ("&&", "||"):
            cc += 1
    return cc


@register
class JavaCyclomaticComplexityRule(Rule):
    code = "JA-X001"
    language = "java"
    category = "complex"
    severity = "warning"
    name = "Java 方法圈复杂度过高"
    description = f"单方法圈复杂度不应超过 {settings.complexity_warn_threshold}。"
    suggestion_template = "拆分方法、合并条件、提取策略。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(MethodDeclaration):
            cc = _java_cyclomatic(node)
            if cc > settings.complexity_warn_threshold:
                line = node.position.line if node.position else 1
                sev = "error" if cc > settings.complexity_critical_threshold else "warning"
                issues.append(Issue(
                    rule_code=self.code,
                    category=self.category,
                    severity=sev,
                    line=line,
                    message=f"方法 '{node.name}' 圈复杂度 {cc} 超过阈值 {settings.complexity_warn_threshold}",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                    suggestion=self.suggestion_template,
                ))
        return issues
