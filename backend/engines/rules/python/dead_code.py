"""
Python 死代码 / 无效代码规则（PY-D001 ~ PY-D004）。
"""
from __future__ import annotations

import ast
from typing import Iterable

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


def _walk_names(nodes: Iterable[ast.AST]) -> set[str]:
    """收集 AST 节点子树中出现的所有 Name/Attribute 标识。"""
    out: set[str] = set()
    for n in nodes:
        for sub in ast.walk(n):
            if isinstance(sub, ast.Name):
                out.add(sub.id)
            elif isinstance(sub, ast.Attribute):
                # 取属性链的最外层名称
                cur: ast.AST = sub
                while isinstance(cur, ast.Attribute):
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    out.add(cur.id)
    return out


@register
class UnusedImportRule(Rule):
    code = "PY-D001"
    language = "python"
    category = "dead"
    severity = "warning"
    name = "未使用的 import"
    description = "导入但未在文件内使用的模块/名称应当移除。"
    suggestion_template = "删除未使用的 import，或使用 # noqa 注释豁免。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        # 收集所有非 import 节点的引用名
        referenced: set[str] = set()
        for node in parsed.ast_root.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            referenced |= _walk_names([node])
        # 也要看模块级以下的代码
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                referenced |= _walk_names(node.body)

        for node in ast.walk(parsed.ast_root):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    used_name = alias.asname or alias.name.split(".")[0]
                    if used_name not in referenced:
                        issues.append(self.make_issue(
                            line=node.lineno,
                            message=f"未使用的 import: {alias.name}",
                            code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                        ))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    used_name = alias.asname or alias.name
                    if used_name not in referenced:
                        issues.append(self.make_issue(
                            line=node.lineno,
                            message=f"未使用的 import: from {node.module} import {alias.name}",
                            code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                        ))
        return issues


@register
class UnusedLocalRule(Rule):
    code = "PY-D002"
    language = "python"
    category = "dead"
    severity = "info"
    name = "未使用的局部变量"
    description = "函数内部赋值但从未使用的局部变量应当移除。"
    suggestion_template = "删除该变量，或重命名为 _ 表示故意忽略。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for func in ast.walk(parsed.ast_root):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            assigned: dict[str, ast.AST] = {}
            for node in ast.walk(func):
                if node is func:
                    continue
                if isinstance(node, ast.Assign):
                    for tgt in node.targets:
                        if isinstance(tgt, ast.Name) and not tgt.id.startswith("_"):
                            assigned.setdefault(tgt.id, tgt)
            referenced: set[str] = set()
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    referenced.add(node.id)
            for name, anchor in assigned.items():
                if name not in referenced:
                    issues.append(self.make_issue(
                        line=anchor.lineno,
                        message=f"局部变量 '{name}' 赋值后未使用",
                        code_snippet=Rule.get_line_snippet(parsed, anchor.lineno),
                    ))
        return issues


@register
class UnreachableCodeRule(Rule):
    code = "PY-D003"
    language = "python"
    category = "dead"
    severity = "error"
    name = "无法到达的代码"
    description = "return/raise/break/continue 后的语句永远不会被执行。"
    suggestion_template = "删除无法到达的代码。"

    _TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            body: list = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
            elif isinstance(node, (ast.For, ast.While, ast.If, ast.Try)):
                body = node.body
            else:
                continue
            for i, stmt in enumerate(body):
                if isinstance(stmt, self._TERMINATORS) and i + 1 < len(body):
                    after = body[i + 1]
                    issues.append(self.make_issue(
                        line=after.lineno,
                        message="此语句之前已 return/raise/break/continue，不可达",
                        code_snippet=Rule.get_line_snippet(parsed, after.lineno),
                    ))
                    break
        return issues


@register
class EmptyFunctionRule(Rule):
    code = "PY-D004"
    language = "python"
    category = "dead"
    severity = "info"
    name = "空函数体"
    description = "函数体仅含 pass 通常是未实现，应至少加注释或抛 NotImplementedError。"
    suggestion_template = "若是抽象/接口，使用 raise NotImplementedError；否则补全实现。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = node.body
            # 跳过有 docstring + pass 的常见占位
            non_doc = [s for s in body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]
            if len(non_doc) == 1 and isinstance(non_doc[0], ast.Pass):
                # 抽象方法/Protocol 跳过
                if any(isinstance(d, ast.Name) and d.id in ("abstractmethod", "abstract") for d in node.decorator_list):
                    continue
                issues.append(self.make_issue(
                    line=node.lineno,
                    message=f"函数 '{node.name}' 仅含 pass，疑似未实现",
                    code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                ))
        return issues
