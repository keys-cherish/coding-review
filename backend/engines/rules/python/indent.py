"""
Python 缩进规则（PY-I001 ~ PY-I002）。
"""
from __future__ import annotations

from backend.engines.parser import ParsedFile, TokenKind
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class IndentSizeRule(Rule):
    code = "PY-I001"
    language = "python"
    category = "indent"
    severity = "warning"
    name = "缩进应使用 4 个空格"
    description = "Python 代码应使用 4 个空格作为单层缩进单位（PEP 8）。"
    suggestion_template = "将缩进改为 4 个空格的倍数。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            stripped = raw.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = raw[: len(raw) - len(stripped)]
            if "\t" in indent:
                continue  # 留给 PY-I002 报
            if indent and len(indent) % 4 != 0:
                issues.append(self.make_issue(
                    line=line_no,
                    message=f"缩进宽度 {len(indent)} 不是 4 的倍数",
                    code_snippet=raw[:80],
                ))
        return issues


@register
class MixedIndentRule(Rule):
    code = "PY-I002"
    language = "python"
    category = "indent"
    severity = "error"
    name = "禁止混用 Tab 和空格作为缩进"
    description = "在同一文件中混用 Tab 和空格会导致难以察觉的缩进错误。"
    suggestion_template = "全文统一为 4 个空格缩进。"

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
            elif " " in indent:
                seen_space = True
            if seen_tab and seen_space:
                break
        if seen_tab and seen_space:
            for line_no, raw in enumerate(parsed.raw_lines, start=1):
                stripped = raw.lstrip()
                indent = raw[: len(raw) - len(stripped)]
                if "\t" in indent:
                    issues.append(self.make_issue(
                        line=line_no,
                        message="文件中混用了 Tab 与空格缩进",
                        code_snippet=raw[:80],
                    ))
                    break
        return issues
