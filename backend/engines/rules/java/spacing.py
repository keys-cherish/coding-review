"""
Java 空格规则（JA-S001）。
"""
from __future__ import annotations

import re

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

# 关键字 + ( 之间应有空格
_BAD_KW_PAREN = re.compile(r"\b(if|for|while|switch|catch|return)\(")


@register
class JavaKeywordParenSpaceRule(Rule):
    code = "JA-S001"
    language = "java"
    category = "space"
    severity = "info"
    name = "关键字与括号之间应有空格"
    description = "if/for/while/switch/catch/return 后应有一个空格再接括号。"
    suggestion_template = "在关键字与括号之间添加一个空格，例如 if (x > 0)。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        in_block_comment = False
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            stripped = raw.strip()
            if in_block_comment:
                if "*/" in stripped:
                    in_block_comment = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_block_comment = True
                continue
            if stripped.startswith("//"):
                continue
            for m in _BAD_KW_PAREN.finditer(raw):
                kw = m.group(1)
                if kw == "return":
                    continue  # return( 实际不严格违反
                issues.append(self.make_issue(
                    line=line_no,
                    column=m.start(),
                    message=f"'{kw}' 与 '(' 之间应有一个空格",
                    code_snippet=raw[:80],
                ))
                break
        return issues
