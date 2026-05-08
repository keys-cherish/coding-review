"""
Java 缩进规则（JA-I001）。
"""
from __future__ import annotations

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class JavaIndentRule(Rule):
    code = "JA-I001"
    language = "java"
    category = "indent"
    severity = "warning"
    name = "Java 应使用统一缩进（4 空格或 Tab，不混用）"
    description = "Java 代码每层应使用 4 个空格或一个 Tab，不应在同一文件中混用。"
    suggestion_template = "全文统一为 4 空格缩进。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        seen_tab = seen_space = False
        for raw in parsed.raw_lines:
            stripped = raw.lstrip()
            if not stripped:
                continue
            indent = raw[: len(raw) - len(stripped)]
            if "\t" in indent:
                seen_tab = True
            elif indent.startswith(" "):
                seen_space = True
            if seen_tab and seen_space:
                break
        if seen_tab and seen_space:
            for line_no, raw in enumerate(parsed.raw_lines, start=1):
                indent = raw[: len(raw) - len(raw.lstrip())]
                if "\t" in indent:
                    issues.append(self.make_issue(
                        line=line_no,
                        message="文件中混用了 Tab 与空格缩进",
                        code_snippet=raw[:80],
                    ))
                    break
        return issues
