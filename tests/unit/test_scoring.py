"""评分引擎单元测试。"""
from __future__ import annotations

from backend.engines.complexity.types import FunctionComplexity
from backend.engines.rules.base import Issue
from backend.engines.scoring.scorer import (
    compute_complexity_score,
    compute_dup_score,
    compute_overall,
    compute_spec_score,
    grade_of,
)


def _issue(severity: str, rule_code: str = "PY001") -> Issue:
    return Issue(
        rule_code=rule_code,
        category="naming",
        severity=severity,
        line=1,
        column=0,
        end_line=1,
        message="test",
    )


class TestGradeOf:

    def test_a(self) -> None:
        assert grade_of(95) == "A"
        assert grade_of(90) == "A"

    def test_b(self) -> None:
        assert grade_of(89.99) == "B"
        assert grade_of(75) == "B"

    def test_c(self) -> None:
        assert grade_of(74.99) == "C"
        assert grade_of(60) == "C"

    def test_d(self) -> None:
        assert grade_of(59.99) == "D"
        assert grade_of(0) == "D"


class TestSpecScore:

    def test_no_issues_full_score(self) -> None:
        score, counts = compute_spec_score([], total_loc=100)
        assert score == 100.0
        assert counts == {"error": 0, "warning": 0, "info": 0}

    def test_errors_lower_score(self) -> None:
        issues = [_issue("error") for _ in range(5)]
        score, counts = compute_spec_score(issues, total_loc=100)
        assert score < 100
        assert counts["error"] == 5

    def test_severity_weighting(self) -> None:
        # 1 个 error 应比 1 个 warning 扣更多
        s_e, _ = compute_spec_score([_issue("error")], total_loc=100)
        s_w, _ = compute_spec_score([_issue("warning")], total_loc=100)
        s_i, _ = compute_spec_score([_issue("info")], total_loc=100)
        assert s_e < s_w < s_i

    def test_zero_loc_does_not_crash(self) -> None:
        score, _ = compute_spec_score([_issue("error")], total_loc=0)
        assert 0 <= score <= 100


class TestDupScore:

    def test_zero_dup(self) -> None:
        assert compute_dup_score(0.0) == 100.0

    def test_high_dup_zero_score(self) -> None:
        assert compute_dup_score(0.6) == 0.0

    def test_monotonic_decreasing(self) -> None:
        prev = 101
        for r in [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]:
            cur = compute_dup_score(r)
            assert cur < prev
            prev = cur


class TestComplexityScore:

    def test_no_metrics_full_score(self) -> None:
        s, counts = compute_complexity_score([], total_loc=100)
        assert s == 100.0

    def test_critical_drops_score_more_than_medium(self) -> None:
        crit = FunctionComplexity("a", "a", 1, 10, 10, 0, 25, 30, 5, "critical")
        med = FunctionComplexity("b", "b", 1, 10, 10, 0, 8, 5, 2, "medium")
        s_c, _ = compute_complexity_score([crit], total_loc=100)
        s_m, _ = compute_complexity_score([med], total_loc=100)
        assert s_c < s_m


class TestOverall:

    def test_clean_project_grade_a(self) -> None:
        breakdown = compute_overall(
            issues=[],
            duplication_rate=0.0,
            metrics=[],
            total_loc=200,
        )
        assert breakdown.overall_score == 100.0
        assert breakdown.grade == "A"

    def test_messy_project_grade_drops(self) -> None:
        issues = [_issue("error") for _ in range(20)] + [_issue("warning") for _ in range(10)]
        crit = [
            FunctionComplexity(f"f{i}", f"f{i}", 1, 30, 30, 0, 25, 30, 5, "critical")
            for i in range(3)
        ]
        breakdown = compute_overall(
            issues=issues,
            duplication_rate=0.25,
            metrics=crit,
            total_loc=300,
        )
        assert breakdown.overall_score < 80
        assert breakdown.error_count == 20
        assert breakdown.warning_count == 10
