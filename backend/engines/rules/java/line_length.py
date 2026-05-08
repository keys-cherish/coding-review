"""
Java 长度规则（JA-L001 行长 / JA-L002 方法长度）。
"""
from __future__ import annotations

from javalang.tree import MethodDeclaration

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

JAVA_LINE_LIMIT = 120
JAVA_METHOD_LIMIT = 80


@register
class JavaLineLengthRule(Rule):
    code = "JA-L001"
    language = "java"
    category = "length"
    severity = "info"
    name = f"单行长度不应超过 {JAVA_LINE_LIMIT} 字符"
    description = f"过长的行影响可读性，建议在 {JAVA_LINE_LIMIT} 字符内换行。"
    suggestion_template = "在合适位置换行或提取局部变量。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            if len(raw) > JAVA_LINE_LIMIT:
                issues.append(self.make_issue(
                    line=line_no,
                    message=f"行长 {len(raw)} 超过 {JAVA_LINE_LIMIT} 字符上限",
                    code_snippet=raw[:120] + ("..." if len(raw) > 120 else ""),
                ))
        return issues


@register
class JavaMethodLengthRule(Rule):
    code = "JA-L002"
    language = "java"
    category = "length"
    severity = "warning"
    name = f"方法长度不应超过 {JAVA_METHOD_LIMIT} 行"
    description = f"过长的方法难以维护，建议拆分（{JAVA_METHOD_LIMIT} 行以内）。"
    suggestion_template = "提取私有方法，按职责拆分。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        # 借助 ParsedFile 已抽取的 functions（带 end_line）
        for f in parsed.functions:
            length = f.end_line - f.start_line + 1
            if length > JAVA_METHOD_LIMIT:
                issues.append(self.make_issue(
                    line=f.start_line,
                    message=f"方法 '{f.name}' 共 {length} 行，超过 {JAVA_METHOD_LIMIT} 行上限",
                    code_snippet=Rule.get_line_snippet(parsed, f.start_line),
                ))
        return issues
