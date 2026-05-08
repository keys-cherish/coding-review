"""
Python 魔法值规则（PY-M001）。
"""
from __future__ import annotations

import ast

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

_ALLOWED_MAGIC_NUMBERS = {0, 1, -1, 2, 0.0, 1.0, -1.0, 100, 1000}


@register
class MagicNumberRule(Rule):
    code = "PY-M001"
    language = "python"
    category = "magic"
    severity = "warning"
    name = "避免使用魔法数字"
    description = "代码中直接出现的数值字面量（除 0、1、-1、2 等常用值）应替换为命名常量。"
    suggestion_template = "将魔法数字提取为有意义的常量，例如 MAX_RETRY = 3。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        # 收集 const 赋值的字面量行号，避免对它们自己再报
        const_assign_lines: set[int] = set()
        for node in parsed.ast_root.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                const_assign_lines.add(node.value.lineno)

        for node in ast.walk(parsed.ast_root):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if isinstance(node.value, bool):
                    continue
                if node.value in _ALLOWED_MAGIC_NUMBERS:
                    continue
                if node.lineno in const_assign_lines:
                    continue
                # 在元数据相关位置（type hints、装饰器参数）中跳过
                issues.append(self.make_issue(
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"魔法数字 {node.value!r}，建议提取为命名常量",
                    code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                ))
        return issues
