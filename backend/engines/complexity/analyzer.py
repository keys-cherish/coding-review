"""
复杂度分析器：综合 cyclomatic + cognitive + 嵌套深度，输出每个函数的全量度量。
"""
from __future__ import annotations

import ast

from javalang.tree import (
    CatchClause as JCatch,
    DoStatement as JDo,
    ForStatement as JFor,
    IfStatement as JIf,
    SwitchStatement as JSwitch,
    WhileStatement as JWhile,
)

from backend.engines.complexity.cognitive import cognitive_java, cognitive_python
from backend.engines.complexity.cyclomatic import cyclomatic_java, cyclomatic_python
from backend.engines.complexity.types import FunctionComplexity, grade_risk
from backend.engines.parser import ParsedFile


def _max_nesting_python(func: ast.AST) -> int:
    """计算 Python 函数最大嵌套深度。"""
    NEST = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)

    def visit(node: ast.AST, depth: int) -> int:
        best = depth
        for child in ast.iter_child_nodes(node):
            d = visit(child, depth + 1 if isinstance(child, NEST) else depth)
            if d > best:
                best = d
        return best

    return visit(func, 0)


def _max_nesting_java(method) -> int:
    """估算 Java 方法最大嵌套深度。"""
    NEST = (JIf, JFor, JWhile, JDo, JSwitch, JCatch)
    if method is None:
        return 0
    max_depth = 0
    for path, node in method:
        if isinstance(node, NEST):
            depth = sum(1 for ancestor in path if isinstance(ancestor, NEST)) + 1
            if depth > max_depth:
                max_depth = depth
    return max_depth


class ComplexityAnalyzer:
    """综合复杂度分析器。"""

    def analyze(self, parsed: ParsedFile) -> list[FunctionComplexity]:
        if parsed.ast_root is None:
            return []
        results: list[FunctionComplexity] = []
        for f in parsed.functions:
            if f.raw_node is None:
                continue
            if parsed.language == "python":
                cc = cyclomatic_python(f.raw_node)
                cog = sum(cognitive_python(c, 0) for c in ast.iter_child_nodes(f.raw_node))
                depth = _max_nesting_python(f.raw_node)
            elif parsed.language == "java":
                cc = cyclomatic_java(f.raw_node)
                cog = cognitive_java(f.raw_node)
                depth = _max_nesting_java(f.raw_node)
            else:
                continue
            results.append(FunctionComplexity(
                function_name=f.name,
                qualified_name=f.qualified_name,
                start_line=f.start_line,
                end_line=f.end_line,
                lines=max(1, f.end_line - f.start_line + 1),
                parameters=len(f.parameters),
                cyclomatic=cc,
                cognitive=cog,
                nesting_depth=depth,
                risk_level=grade_risk(cc),
            ))
        return results
