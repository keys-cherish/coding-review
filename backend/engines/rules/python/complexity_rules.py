"""
Python 复杂度相关规则（PY-X001 圈复杂度 / PY-X002 嵌套深度）。

规则本身不重复实现复杂度算法，而是通过复杂度引擎得到的结果间接产生问题。
此处提供基于 AST 直接检测的轻量版本，作为规则系统中的可见入口。
"""
from __future__ import annotations

import ast

from backend.config import settings
from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

NESTING_LIMIT = 4


def _cyclomatic(func: ast.AST) -> int:
    """快速计算单函数 McCabe 圈复杂度。"""
    cc = 1
    for n in ast.walk(func):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert)):
            cc += 1
        elif isinstance(n, ast.BoolOp):
            cc += max(0, len(n.values) - 1)
        elif isinstance(n, ast.IfExp):
            cc += 1
        elif isinstance(n, ast.comprehension):
            cc += 1
            cc += len(n.ifs)
        elif isinstance(n, ast.Match):
            cc += len(n.cases)
    return cc


def _max_depth(func: ast.AST) -> int:
    """计算函数体最大嵌套深度。"""
    NEST = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)

    def visit(node: ast.AST, depth: int) -> int:
        best = depth
        for child in ast.iter_child_nodes(node):
            d = visit(child, depth + 1 if isinstance(child, NEST) else depth)
            if d > best:
                best = d
        return best

    return visit(func, 0)


@register
class CyclomaticComplexityRule(Rule):
    code = "PY-X001"
    language = "python"
    category = "complex"
    severity = "warning"
    name = "圈复杂度过高"
    description = f"单函数圈复杂度不应超过 {settings.complexity_warn_threshold}。"
    suggestion_template = "拆分函数、合并条件、提取策略对象。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cc = _cyclomatic(node)
                if cc > settings.complexity_warn_threshold:
                    sev = "error" if cc > settings.complexity_critical_threshold else "warning"
                    issues.append(Issue(
                        rule_code=self.code,
                        category=self.category,
                        severity=sev,
                        line=node.lineno,
                        message=f"函数 '{node.name}' 圈复杂度 {cc} 超过阈值 {settings.complexity_warn_threshold}",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                        suggestion=self.suggestion_template,
                    ))
        return issues


@register
class NestingDepthRule(Rule):
    code = "PY-X002"
    language = "python"
    category = "complex"
    severity = "warning"
    name = "嵌套层级过深"
    description = f"函数内最大嵌套不应超过 {NESTING_LIMIT} 层。"
    suggestion_template = "提前 return 或提取子函数减少嵌套。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                d = _max_depth(node)
                if d > NESTING_LIMIT:
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message=f"函数 '{node.name}' 最大嵌套 {d} 层，超过 {NESTING_LIMIT}",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
        return issues
