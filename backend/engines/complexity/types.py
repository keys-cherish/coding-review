"""
复杂度引擎数据结构。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FunctionComplexity:
    """单个函数/方法的复杂度度量。"""
    function_name: str
    qualified_name: str
    start_line: int
    end_line: int
    lines: int
    parameters: int
    cyclomatic: int           # McCabe 圈复杂度
    cognitive: int            # SonarSource 认知复杂度
    nesting_depth: int        # 最大嵌套深度
    risk_level: str           # low / medium / high / critical


def grade_risk(cyclomatic: int) -> str:
    """根据圈复杂度划分风险等级。"""
    if cyclomatic <= 5:
        return "low"
    if cyclomatic <= 10:
        return "medium"
    if cyclomatic <= 20:
        return "high"
    return "critical"
