"""规则引擎单元测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.engines.parser import parse_file
from backend.engines.rules.registry import discover_rules, rule_registry


@pytest.fixture(scope="module", autouse=True)
def _ensure_rules_loaded() -> None:
    """确保所有内置规则被发现和注册。"""
    discover_rules()


def _run_lang_rules(parsed) -> list:
    issues = []
    for rule in rule_registry.by_language(parsed.language):
        issues.extend(rule.check(parsed))
    return issues


class TestRegistry:

    def test_registry_has_python_rules(self) -> None:
        py_rules = [r for r in rule_registry.all_rules() if r.language == "python"]
        assert len(py_rules) >= 5

    def test_registry_has_java_rules(self) -> None:
        ja_rules = [r for r in rule_registry.all_rules() if r.language == "java"]
        assert len(ja_rules) >= 5

    def test_no_duplicate_codes(self) -> None:
        codes = [r.code for r in rule_registry.all_rules()]
        assert len(codes) == len(set(codes))

    def test_enable_disable_round_trip(self) -> None:
        rule = rule_registry.all_rules()[0]
        original = rule.enabled
        try:
            rule_registry.disable(rule.code)
            assert rule.enabled is False
            rule_registry.enable(rule.code)
            assert rule.enabled is True
        finally:
            rule.enabled = original

    def test_stats_shape(self) -> None:
        st = rule_registry.stats()
        assert "total" in st
        assert "by_language" in st
        assert "by_severity" in st
        assert st["total"] == len(rule_registry.all_rules())


class TestPythonRulesAgainstFixtures:

    def test_clean_fixture_few_issues(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "clean.py")
        issues = _run_lang_rules(parsed)
        # 干净文件应该没有 error 级别问题
        errors = [i for i in issues if i.severity == "error"]
        assert errors == [], f"clean.py 不应该有 error: {[i.rule_code for i in errors]}"

    def test_messy_fixture_triggers_many_rules(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "messy.py")
        issues = _run_lang_rules(parsed)
        codes = {i.rule_code for i in issues}
        # 至少触发 3 个不同规则
        assert len(codes) >= 3
        # 应包含命名相关
        assert any(c.startswith("PY-N") for c in codes)

    def test_issues_have_required_fields(self, py_fixture_dir: Path) -> None:
        parsed = parse_file(py_fixture_dir / "messy.py")
        issues = _run_lang_rules(parsed)
        assert issues, "messy.py 应该产生若干 issue"
        for it in issues:
            assert it.rule_code
            assert it.severity in {"error", "warning", "info"}
            assert it.line >= 1
            assert it.message
