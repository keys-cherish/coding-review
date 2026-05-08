"""
质量评分引擎。

三维评分（每维 0-100，越高越好）：
- spec_score（规范度）：基于 issue 严重等级加权扣分
- dup_score（重复度）：基于重复率
- complexity_score（复杂度）：基于高复杂度函数比例

综合评分：
    overall = w_spec * spec_score
            + w_dup  * dup_score
            + w_cx   * complexity_score
权重在 settings 中配置（默认 0.45 / 0.30 / 0.25）。

等级：
    [90,100] A 优秀
    [75, 90) B 良好
    [60, 75) C 中等
    [ 0, 60) D 不及格

设计要点（详细设计文档会引用此处推导）：
- 规范度扣分按"每千行加权问题数"做归一化，避免大项目天然吃亏
- 重复度采用线性映射：5% 重复扣 10 分，20% 扣 40 分，超过 50% 直接 0
- 复杂度按 risk 桶（critical=10, high=5, medium=2）累计扣分
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings
from backend.engines.complexity import FunctionComplexity
from backend.engines.rules.base import Issue


@dataclass
class ScoreBreakdown:
    """评分明细。"""
    spec_score: float
    dup_score: float
    complexity_score: float
    overall_score: float
    grade: str  # A/B/C/D
    error_count: int
    warning_count: int
    info_count: int


def grade_of(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_spec_score(issues: list[Issue], total_loc: int) -> tuple[float, dict]:
    """计算规范度评分。"""
    if total_loc <= 0:
        total_loc = 1
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        if issue.severity in counts:
            counts[issue.severity] += 1

    # 加权问题数（按每千行）
    weighted_per_kloc = (
        counts["error"] * 5
        + counts["warning"] * 2
        + counts["info"] * 0.5
    ) / total_loc * 1000

    # 经验映射：每千行加权扣 1 分，最多扣 100 分
    score = _clip(100 - weighted_per_kloc, 0, 100)
    return round(score, 2), counts


def compute_dup_score(duplication_rate: float) -> float:
    """计算重复度评分。"""
    # 线性：5% 扣 10 分，10% 扣 20 分；50% 扣 100 分
    deduct = duplication_rate * 200  # 0~200
    return round(_clip(100 - deduct, 0, 100), 2)


def compute_complexity_score(
    metrics: list[FunctionComplexity],
    total_loc: int,
) -> tuple[float, dict]:
    """计算复杂度评分。"""
    if total_loc <= 0:
        total_loc = 1
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for m in metrics:
        if m.risk_level in counts:
            counts[m.risk_level] += 1

    weighted = (
        counts["critical"] * 10
        + counts["high"] * 5
        + counts["medium"] * 2
    ) / total_loc * 1000

    score = _clip(100 - weighted, 0, 100)
    return round(score, 2), counts


def compute_overall(
    issues: list[Issue],
    duplication_rate: float,
    metrics: list[FunctionComplexity],
    total_loc: int,
) -> ScoreBreakdown:
    """综合评分入口。"""
    spec, severity_counts = compute_spec_score(issues, total_loc)
    dup = compute_dup_score(duplication_rate)
    cx, _ = compute_complexity_score(metrics, total_loc)

    overall = (
        settings.score_weight_spec * spec
        + settings.score_weight_dup * dup
        + settings.score_weight_complexity * cx
    )
    overall = round(_clip(overall, 0, 100), 2)

    return ScoreBreakdown(
        spec_score=spec,
        dup_score=dup,
        complexity_score=cx,
        overall_score=overall,
        grade=grade_of(overall),
        error_count=severity_counts.get("error", 0),
        warning_count=severity_counts.get("warning", 0),
        info_count=severity_counts.get("info", 0),
    )
