"""
McCabe 圈复杂度（Cyclomatic Complexity）实现。

算法基于 Thomas McCabe 1976 年论文：
    CC = E - N + 2P
其中 E 是控制流图边数，N 是节点数，P 是连通分量数。
对程序而言，等价的简化公式为：
    CC = 决策点数 + 1
决策点包括：if、elif、for、while、case、catch、和短路布尔运算符（and/or 或 && / ||）。

参考：
    McCabe, T. J. (1976). A Complexity Measure. IEEE TSE.
"""
from __future__ import annotations

import ast

import javalang
from javalang.tree import (
    BinaryOperation as JBinaryOp,
    CatchClause as JCatch,
    DoStatement as JDo,
    ForStatement as JFor,
    IfStatement as JIf,
    SwitchStatementCase as JCase,
    TernaryExpression as JTernary,
    WhileStatement as JWhile,
)

from backend.engines.parser import ParsedFile


def cyclomatic_python(func: ast.AST) -> int:
    """计算 Python 函数 AST 的圈复杂度。"""
    cc = 1
    for node in ast.walk(func):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert)):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            cc += max(0, len(node.values) - 1)
        elif isinstance(node, ast.IfExp):
            cc += 1
        elif isinstance(node, ast.comprehension):
            cc += 1
            cc += len(node.ifs)
        elif isinstance(node, ast.Match):
            cc += len(node.cases)
    return cc


_J_DECISION = (JIf, JFor, JWhile, JDo, JCatch, JCase, JTernary)


def cyclomatic_java(method) -> int:
    """计算 Java 方法 AST 的圈复杂度。"""
    cc = 1
    if method is None:
        return cc
    for path, node in method:
        if isinstance(node, _J_DECISION):
            cc += 1
        elif isinstance(node, JBinaryOp) and node.operator in ("&&", "||"):
            cc += 1
    return cc


def compute_for_file(parsed: ParsedFile) -> dict[str, int]:
    """以函数限定名为键，返回每个函数的圈复杂度。"""
    out: dict[str, int] = {}
    if parsed.ast_root is None:
        return out
    if parsed.language == "python":
        for f in parsed.functions:
            if f.raw_node is not None:
                out[f.qualified_name] = cyclomatic_python(f.raw_node)
    elif parsed.language == "java":
        for f in parsed.functions:
            if f.raw_node is not None:
                out[f.qualified_name] = cyclomatic_java(f.raw_node)
    return out
