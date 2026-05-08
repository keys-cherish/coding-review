"""
Python 注释规则（PY-C001 ~ PY-C003）。
"""
from __future__ import annotations

import ast

from backend.engines.parser import ParsedFile, TokenKind
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class PublicFunctionDocstringRule(Rule):
    code = "PY-C001"
    language = "python"
    category = "comment"
    severity = "info"
    name = "公开函数应有 docstring"
    description = "所有 public（不以 _ 开头）函数都应有 docstring 说明用途。"
    suggestion_template = '在函数体首行添加 """简要说明""" 文档字符串。'

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                if ast.get_docstring(node) is None:
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message=f"公开函数 '{node.name}' 缺少 docstring",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
        return issues


@register
class PublicClassDocstringRule(Rule):
    code = "PY-C002"
    language = "python"
    category = "comment"
    severity = "info"
    name = "公开类应有 docstring"
    description = "所有 public 类都应有 docstring 说明职责。"
    suggestion_template = '在类体首行添加 """职责说明""" 文档字符串。'

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                if ast.get_docstring(node) is None:
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message=f"公开类 '{node.name}' 缺少 docstring",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
        return issues


@register
class CommentSpaceRule(Rule):
    code = "PY-C003"
    language = "python"
    category = "comment"
    severity = "info"
    name = "# 与注释文字之间应有空格"
    description = "行内注释 # 后应有一个空格，便于阅读。"
    suggestion_template = "在 # 后加一个空格，例如 # 这是注释。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for tok in parsed.tokens:
            if tok.kind != TokenKind.COMMENT:
                continue
            text = tok.value
            if text.startswith("#!"):  # shebang
                continue
            if len(text) > 1 and text[1] not in (" ", "!", "#"):
                issues.append(self.make_issue(
                    line=tok.line,
                    column=tok.column,
                    message="注释 # 后应跟一个空格",
                    code_snippet=text[:80],
                ))
        return issues
