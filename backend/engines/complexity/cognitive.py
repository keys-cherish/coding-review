"""
认知复杂度（Cognitive Complexity）实现。

算法基于 SonarSource 的 G. Ann Campbell 论文：
    "Cognitive Complexity – a new way of measuring understandability"

核心思想（与 McCabe 不同）：
1. 嵌套结构造成额外认知成本，按嵌套深度累加（深一层加 1）
2. 跳出常规线性流程的关键字（break/continue/goto）+1
3. 短路布尔运算符序列只算一次（避免短路链造成虚高）

实现说明：
- 此处实现的是简化但符合 SonarSource 主要规则的版本
- Python 与 Java 共用一套递归遍历框架，由语言适配器返回子节点
"""
from __future__ import annotations

import ast

from javalang.tree import (
    BinaryOperation as JBinaryOp,
    BreakStatement as JBreak,
    CatchClause as JCatch,
    ContinueStatement as JContinue,
    DoStatement as JDo,
    ForStatement as JFor,
    IfStatement as JIf,
    SwitchStatement as JSwitch,
    TernaryExpression as JTernary,
    WhileStatement as JWhile,
)

from backend.engines.parser import ParsedFile


# ========== Python 实现 ==========
_PY_NEST = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try)
_PY_FLOW_BREAK = (ast.Break, ast.Continue)


def cognitive_python(node: ast.AST, depth: int = 0) -> int:
    """递归计算 Python 节点子树的认知复杂度。"""
    score = 0
    if isinstance(node, _PY_NEST):
        score += 1 + depth  # 基础 +1，嵌套加成
        depth += 1
    elif isinstance(node, ast.IfExp):
        score += 1 + depth
    elif isinstance(node, _PY_FLOW_BREAK):
        score += 1
    elif isinstance(node, ast.BoolOp):
        # 同种连续短路只算一次（这里用 values 数 - 1 作为近似）
        score += max(0, len(node.values) - 1)
    elif isinstance(node, ast.ExceptHandler):
        score += 1 + depth

    for child in ast.iter_child_nodes(node):
        score += cognitive_python(child, depth)
    return score


# ========== Java 实现 ==========
_J_NEST = (JIf, JFor, JWhile, JDo, JSwitch, JCatch)
_J_FLOW_BREAK = (JBreak, JContinue)


def cognitive_java(method) -> int:
    """计算 Java 方法的认知复杂度。

    用 javalang 的 path 信息估算嵌套深度。
    """
    if method is None:
        return 0

    score = 0
    last_bool_op: str | None = None

    for path, node in method:
        # 计算当前嵌套深度：path 中嵌套结构的数量
        depth = sum(1 for ancestor in path if isinstance(ancestor, _J_NEST))
        if isinstance(node, _J_NEST):
            score += 1 + depth
        elif isinstance(node, JTernary):
            score += 1 + depth
        elif isinstance(node, _J_FLOW_BREAK):
            score += 1
        elif isinstance(node, JBinaryOp) and node.operator in ("&&", "||"):
            if last_bool_op != node.operator:
                score += 1
                last_bool_op = node.operator
        else:
            last_bool_op = None
    return score


def compute_for_file(parsed: ParsedFile) -> dict[str, int]:
    """以函数限定名为键，返回每个函数的认知复杂度。"""
    out: dict[str, int] = {}
    if parsed.ast_root is None:
        return out
    if parsed.language == "python":
        for f in parsed.functions:
            if f.raw_node is not None:
                # 函数体节点，跳过对 def 自身的入口加成
                inner = 0
                for child in ast.iter_child_nodes(f.raw_node):
                    inner += cognitive_python(child, 0)
                out[f.qualified_name] = inner
    elif parsed.language == "java":
        for f in parsed.functions:
            if f.raw_node is not None:
                out[f.qualified_name] = cognitive_java(f.raw_node)
    return out
