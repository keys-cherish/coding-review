"""
Java 魔法值规则（JA-M001）。
"""
from __future__ import annotations

from javalang.tree import Literal

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

_ALLOWED_LITERALS = {"0", "1", "-1", "2", "0L", "1L", "0.0", "1.0", "100", "1000"}


@register
class JavaMagicNumberRule(Rule):
    code = "JA-M001"
    language = "java"
    category = "magic"
    severity = "warning"
    name = "避免使用魔法数字"
    description = "代码中直接出现的数值字面量（除 0、1、-1、2 等）应替换为命名常量。"
    suggestion_template = "提取为 static final 常量，例如 private static final int MAX = 100;"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        # 收集 final 字段中的字面量行号，避免对常量定义本身报错
        const_lines: set[int] = set()
        from javalang.tree import FieldDeclaration
        for _, fd in parsed.ast_root.filter(FieldDeclaration):
            mods = fd.modifiers or set()
            if "final" in mods and fd.position:
                const_lines.add(fd.position.line)

        for _, node in parsed.ast_root.filter(Literal):
            if node.position is None:
                continue
            if node.position.line in const_lines:
                continue
            value = node.value
            if value in (None, "true", "false") or value.startswith('"') or value.startswith("'"):
                continue
            cleaned = value.rstrip("LlFfDd")
            if cleaned in _ALLOWED_LITERALS or cleaned.lstrip("-") in _ALLOWED_LITERALS:
                continue
            try:
                float(cleaned)
            except ValueError:
                continue
            issues.append(self.make_issue(
                line=node.position.line,
                column=node.position.column,
                message=f"魔法数字 {value}",
                code_snippet=Rule.get_line_snippet(parsed, node.position.line),
            ))
        return issues
