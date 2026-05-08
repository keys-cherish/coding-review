"""复杂度引擎单元测试。"""
from __future__ import annotations

import ast
from pathlib import Path

from backend.engines.complexity import (
    ComplexityAnalyzer,
    cognitive_python,
    cyclomatic_python,
    grade_risk,
)
from backend.engines.parser import parse_file


def _first_func(code: str) -> ast.FunctionDef:
    tree = ast.parse(code)
    return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))


class TestCyclomatic:

    def test_baseline_is_one(self) -> None:
        node = _first_func("def f():\n    return 1\n")
        assert cyclomatic_python(node) == 1

    def test_if_adds_one(self) -> None:
        node = _first_func("def f(x):\n    if x:\n        return 1\n    return 0\n")
        assert cyclomatic_python(node) == 2

    def test_chained_decisions(self) -> None:
        code = (
            "def f(a, b, c):\n"
            "    if a:\n"
            "        if b:\n"
            "            if c:\n"
            "                return 1\n"
            "    for i in range(10):\n"
            "        pass\n"
            "    return 0\n"
        )
        node = _first_func(code)
        # 3 个 if + 1 个 for = +4
        assert cyclomatic_python(node) == 5

    def test_boolean_short_circuit(self) -> None:
        node = _first_func("def f(a, b, c):\n    return a and b and c\n")
        # `and` 三元短路 = +2
        assert cyclomatic_python(node) == 3


class TestCognitive:

    def test_baseline_zero(self) -> None:
        node = _first_func("def f():\n    return 1\n")
        assert cognitive_python(node) == 0

    def test_nesting_increases(self) -> None:
        code = (
            "def f(a, b):\n"
            "    if a:\n"
            "        if b:\n"
            "            return 1\n"
            "    return 0\n"
        )
        node = _first_func(code)
        # 外层 if=1，嵌套 if=2 → 总 3
        assert cognitive_python(node) >= 3


class TestGradeRisk:

    def test_low_risk(self) -> None:
        assert grade_risk(1) == "low"
        assert grade_risk(5) == "low"

    def test_medium_risk(self) -> None:
        assert grade_risk(6) == "medium"
        assert grade_risk(10) == "medium"

    def test_high_risk(self) -> None:
        assert grade_risk(11) == "high"
        assert grade_risk(20) == "high"

    def test_critical_risk(self) -> None:
        assert grade_risk(21) == "critical"
        assert grade_risk(100) == "critical"


class TestAnalyzer:

    def test_messy_file_yields_metrics(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "messy.py")
        analyzer = ComplexityAnalyzer()
        metrics = analyzer.analyze(parsed)
        assert len(metrics) >= 3
        # 至少存在一个 medium 及以上风险
        risk_levels = {m.risk_level for m in metrics}
        assert risk_levels & {"medium", "high", "critical"}

    def test_clean_file_low_risk(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "clean.py")
        metrics = ComplexityAnalyzer().analyze(parsed)
        assert all(m.risk_level == "low" for m in metrics)
