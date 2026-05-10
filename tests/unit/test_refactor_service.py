"""重构建议聚合器单元测试（仅生成器部分）。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from backend.engines.architecture.dependency_graph import (
    DependencyEdge,
    DependencyGraph,
    ModuleNode,
)
from backend.services.refactor_service import (
    Suggestion,
    _from_complex_functions,
    _from_cycles,
    _from_duplications,
    _from_layer_violations,
    _from_smell_issues,
)


def _mk_metric(**kw) -> MagicMock:
    m = MagicMock()
    m.source_file_id = kw.get("source_file_id", 1)
    m.function_name = kw.get("function_name", "do_stuff")
    m.start_line = kw.get("start_line", 10)
    m.cyclomatic = kw.get("cyclomatic", 5)
    m.cognitive = kw.get("cognitive", 5)
    m.lines = kw.get("lines", 30)
    m.parameters = kw.get("parameters", 2)
    return m


def _mk_issue(rule_code: str, source_file_id: int = 1, line: int = 1) -> MagicMock:
    iss = MagicMock()
    iss.rule_code = rule_code
    iss.source_file_id = source_file_id
    iss.line = line
    iss.message = "上帝类 Foo：方法数 30 > 20"
    iss.suggestion = "拆分类"
    return iss


def _mk_dup(**kw) -> MagicMock:
    d = MagicMock()
    d.fingerprint = kw.get("fingerprint", "abc123")
    d.occurrences = kw.get("occurrences", 3)
    d.token_length = kw.get("token_length", 50)
    d.line_length = kw.get("line_length", 15)
    d.detection_method = kw.get("detection_method", "token")
    d.occurrences_json = json.dumps(kw.get("occurrences_list", [
        {"file": "a.py", "start_line": 10},
        {"file": "b.py", "start_line": 20},
    ]))
    return d


class TestSuggestionPriority:

    def test_high_impact_low_effort_scores_highest(self) -> None:
        s = Suggestion(id="x", category="x", title="", rationale="",
                       impact="high", effort="low")
        s.compute_priority()
        assert s.priority >= 90

    def test_low_impact_high_effort_scores_lowest(self) -> None:
        s = Suggestion(id="x", category="x", title="", rationale="",
                       impact="low", effort="high")
        s.compute_priority()
        assert s.priority <= 20


class TestFromComplexFunctions:

    def test_selects_only_hot_functions(self) -> None:
        metrics = [
            _mk_metric(cyclomatic=3, cognitive=2, lines=20),   # 冷
            _mk_metric(function_name="big", cyclomatic=25, lines=120),
        ]
        files = {1: "svc/user.py"}
        out = _from_complex_functions(metrics, files)
        assert len(out) == 1
        assert out[0].category == "method_decomp"
        assert "big" in out[0].title
        assert out[0].impact == "high"

    def test_empty(self) -> None:
        assert _from_complex_functions([], {}) == []


class TestFromSmellIssues:

    def test_god_class_issue_produces_class_split(self) -> None:
        out = _from_smell_issues([_mk_issue("PY-SM001")], {1: "mod.py"})
        assert len(out) == 1
        assert out[0].category == "class_split"
        assert out[0].impact == "high"

    def test_long_param_produces_arg_object(self) -> None:
        out = _from_smell_issues([_mk_issue("JAVA-SM004", line=42)], {1: "X.java"})
        assert out[0].category == "arg_object"
        assert out[0].effort == "low"

    def test_unknown_rule_ignored(self) -> None:
        out = _from_smell_issues([_mk_issue("UNKNOWN")], {1: "a.py"})
        assert out == []


class TestFromDuplications:

    def test_heavy_duplication_wins(self) -> None:
        dups = [
            _mk_dup(line_length=5, occurrences=2),   # 太小，应跳过
            _mk_dup(line_length=40, occurrences=4, fingerprint="bigdup"),
        ]
        out = _from_duplications(dups)
        assert len(out) == 1
        assert out[0].category == "dup"
        assert "4 处" in out[0].title


class TestFromCyclesAndLayers:

    def test_layer_violation_grouping(self) -> None:
        g = DependencyGraph()
        for f in ["controller/a.py", "repository/b.py"]:
            mid = f.replace("/", ".").removesuffix(".py")
            g.nodes[mid] = ModuleNode(module_id=mid, file_path=f, language="python")
        g.edges[("controller.a", "repository.b")] = DependencyEdge(
            src="controller.a", dst="repository.b",
        )
        g.adjacency["controller.a"].add("repository.b")

        out = _from_layer_violations(g)
        assert len(out) == 1
        assert out[0].category == "layer"
        assert "controller" in out[0].title
        assert "repository" in out[0].title

    def test_no_cycles_no_suggestions(self) -> None:
        g = DependencyGraph()
        g.nodes["a"] = ModuleNode(module_id="a", file_path="a.py", language="python")
        g.nodes["b"] = ModuleNode(module_id="b", file_path="b.py", language="python")
        g.edges[("a", "b")] = DependencyEdge(src="a", dst="b")
        g.adjacency["a"].add("b")
        out = _from_cycles(g)
        assert out == []
