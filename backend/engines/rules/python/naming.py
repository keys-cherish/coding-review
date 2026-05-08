"""
Python 命名规范规则（PY-N001 ~ PY-N005）。

参考 PEP 8 命名约定。
"""
from __future__ import annotations

import ast
import re

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

# ---------- 正则 ----------
_RE_SNAKE_LOWER = re.compile(r"^[a-z_][a-z0-9_]*$")
_RE_PASCAL = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_RE_UPPER_SNAKE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_RE_MODULE = re.compile(r"^[a-z][a-z0-9_]*$")

_ALLOWED_SHORT_VARS = {"i", "j", "k", "n", "m", "x", "y", "z", "_", "T", "K", "V", "e"}


@register
class ModuleNamingRule(Rule):
    code = "PY-N001"
    language = "python"
    category = "naming"
    severity = "warning"
    name = "模块名应使用小写下划线命名"
    description = "Python 模块（文件）名应使用全小写字母与下划线，避免大小写混合或连字符。"
    suggestion_template = "将文件名改为全小写下划线形式，例如 my_module.py。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        stem = parsed.file_path.stem
        if stem in {"__init__", "__main__"}:
            return []
        if not _RE_MODULE.match(stem):
            return [self.make_issue(
                line=1,
                message=f"模块名 '{parsed.file_path.name}' 不符合小写下划线规范",
                code_snippet=parsed.file_path.name,
            )]
        return []


@register
class ClassNamingRule(Rule):
    code = "PY-N002"
    language = "python"
    category = "naming"
    severity = "error"
    name = "类名应使用 PascalCase"
    description = "类名应采用首字母大写的驼峰式（PascalCase）。"
    suggestion_template = "将类名改写为 PascalCase，例如 UserAccount。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, ast.ClassDef) and not _RE_PASCAL.match(node.name):
                issues.append(self.make_issue(
                    line=node.lineno,
                    column=node.col_offset,
                    message=f"类名 '{node.name}' 不符合 PascalCase",
                    code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                ))
        return issues


@register
class FunctionNamingRule(Rule):
    code = "PY-N003"
    language = "python"
    category = "naming"
    severity = "warning"
    name = "函数与方法应使用 snake_case"
    description = "函数与方法名应使用全小写下划线（snake_case），允许前导下划线表示私有。"
    suggestion_template = "将函数名改写为 snake_case，例如 calculate_total。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name_to_check = node.name.lstrip("_") or node.name
                if not _RE_SNAKE_LOWER.match(name_to_check):
                    issues.append(self.make_issue(
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"函数名 '{node.name}' 不符合 snake_case",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
        return issues


@register
class ConstantNamingRule(Rule):
    code = "PY-N004"
    language = "python"
    category = "naming"
    severity = "info"
    name = "模块级常量应使用全大写下划线"
    description = "模块级别的常量（赋值的字面量）应采用 UPPER_SNAKE_CASE 命名。"
    suggestion_template = "将常量改写为全大写下划线形式，例如 MAX_RETRY = 3。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in parsed.ast_root.body:  # 仅模块顶层
            if isinstance(node, ast.Assign):
                value = node.value
                if not isinstance(value, ast.Constant):
                    continue
                if isinstance(value.value, bool):  # True/False 通常是模块级配置标志，跳过
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        nm = target.id
                        if nm.startswith("_"):
                            continue
                        if not _RE_UPPER_SNAKE.match(nm):
                            issues.append(self.make_issue(
                                line=target.lineno,
                                column=target.col_offset,
                                message=f"模块级常量 '{nm}' 应使用 UPPER_SNAKE_CASE",
                                code_snippet=Rule.get_line_snippet(parsed, target.lineno),
                            ))
        return issues


@register
class SingleLetterVariableRule(Rule):
    code = "PY-N005"
    language = "python"
    category = "naming"
    severity = "info"
    name = "避免使用单字母变量"
    description = "除循环计数器（i,j,k）和数学符号（x,y,z）外，不应使用单字母变量。"
    suggestion_template = "用更具描述性的变量名替代，例如 user_count、total_amount。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and len(tgt.id) == 1 and tgt.id not in _ALLOWED_SHORT_VARS:
                        issues.append(self.make_issue(
                            line=tgt.lineno,
                            column=tgt.col_offset,
                            message=f"避免单字母变量 '{tgt.id}'",
                            code_snippet=Rule.get_line_snippet(parsed, tgt.lineno),
                        ))
        return issues
