"""
Python 长度规则（PY-L001 行长度 / PY-L002 函数长度）。
"""
from __future__ import annotations

import ast

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

LINE_LENGTH_LIMIT = 100
FUNCTION_LENGTH_LIMIT = 50


@register
class LineLengthRule(Rule):
    code = "PY-L001"
    language = "python"
    category = "length"
    severity = "info"
    name = f"单行长度不应超过 {LINE_LENGTH_LIMIT} 字符"
    description = f"过长的行影响可读性，建议在 {LINE_LENGTH_LIMIT} 字符内换行。"
    suggestion_template = "在合适位置换行或提取变量。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            if len(raw) > LINE_LENGTH_LIMIT:
                issues.append(self.make_issue(
                    line=line_no,
                    message=f"行长 {len(raw)} 超过 {LINE_LENGTH_LIMIT} 字符上限",
                    code_snippet=raw[:120] + ("..." if len(raw) > 120 else ""),
                ))
        return issues


@register
class FunctionLengthRule(Rule):
    code = "PY-L002"
    language = "python"
    category = "length"
    severity = "warning"
    name = f"函数长度不应超过 {FUNCTION_LENGTH_LIMIT} 行"
    description = f"过长的函数难以理解和维护，建议拆分为多个小函数（{FUNCTION_LENGTH_LIMIT} 行以内）。"
    suggestion_template = "提取子函数，按职责拆分。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno) or node.lineno
                length = end - node.lineno + 1
                if length > FUNCTION_LENGTH_LIMIT:
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message=f"函数 '{node.name}' 共 {length} 行，超过 {FUNCTION_LENGTH_LIMIT} 行上限",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
        return issues
