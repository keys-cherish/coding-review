"""坏味道检测器单元测试。"""
from __future__ import annotations

from pathlib import Path

from backend.engines.parser import parse_file
from backend.engines.smells import (
    SmellThresholds,
    detect_fat_interfaces,
    detect_god_classes,
    detect_god_methods,
    detect_long_parameter_lists,
)


def _parse_python(code: str, tmp_path: Path) -> "object":
    fp = tmp_path / "mod.py"
    fp.write_text(code, encoding="utf-8")
    return parse_file(fp)


class TestGodClass:

    def test_detects_class_with_many_methods(self, tmp_path: Path) -> None:
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(22))
        code = f"class Big:\n{methods}\n"
        parsed = _parse_python(code, tmp_path)
        issues = detect_god_classes(parsed)
        assert issues, "应识别方法数过多为上帝类"
        assert "方法数" in issues[0].message
        assert issues[0].rule_code == "SMELL-GOD-CLASS"

    def test_detects_class_with_many_fields(self, tmp_path: Path) -> None:
        fields = "\n".join(f"        self.f{i} = 0" for i in range(25))
        code = f"class Big:\n    def __init__(self):\n{fields}\n"
        parsed = _parse_python(code, tmp_path)
        issues = detect_god_classes(parsed)
        assert issues
        assert "字段数" in issues[0].message

    def test_small_class_ok(self, tmp_path: Path) -> None:
        parsed = _parse_python(
            "class Small:\n    def a(self): pass\n    def b(self): pass\n",
            tmp_path,
        )
        assert detect_god_classes(parsed) == []

    def test_custom_thresholds(self, tmp_path: Path) -> None:
        code = "class Mid:\n" + "\n".join(f"    def m{i}(self): pass" for i in range(6))
        parsed = _parse_python(code, tmp_path)
        assert detect_god_classes(parsed) == []
        th = SmellThresholds(god_class_methods=5)
        assert detect_god_classes(parsed, th)


class TestGodMethod:

    def test_detects_long_function(self, tmp_path: Path) -> None:
        body = "\n".join(f"    x = {i}" for i in range(90))
        code = f"def huge():\n{body}\n"
        parsed = _parse_python(code, tmp_path)
        issues = detect_god_methods(parsed)
        assert issues
        assert any("函数" in i.message for i in issues)

    def test_detects_high_complexity(self, tmp_path: Path) -> None:
        branches = "\n".join(f"    if x == {i}: y = {i}" for i in range(18))
        code = f"def branchy(x):\n{branches}\n    return 0\n"
        parsed = _parse_python(code, tmp_path)
        issues = detect_god_methods(parsed)
        assert issues

    def test_normal_function_ok(self, tmp_path: Path) -> None:
        parsed = _parse_python("def ok():\n    return 1\n", tmp_path)
        assert detect_god_methods(parsed) == []


class TestLongParamList:

    def test_too_many_params(self, tmp_path: Path) -> None:
        parsed = _parse_python(
            "def f(a, b, c, d, e, f, g): pass\n",
            tmp_path,
        )
        issues = detect_long_parameter_lists(parsed)
        assert issues
        assert "参数过多" in issues[0].message

    def test_self_not_counted(self, tmp_path: Path) -> None:
        parsed = _parse_python(
            "class C:\n    def m(self, a, b, c, d, e): pass\n",
            tmp_path,
        )
        assert detect_long_parameter_lists(parsed) == []

    def test_within_limit_ok(self, tmp_path: Path) -> None:
        parsed = _parse_python("def ok(a, b, c): pass\n", tmp_path)
        assert detect_long_parameter_lists(parsed) == []


class TestFatInterface:
    """仅 Java，这里用结构化 mock 验证语言过滤。"""

    def test_python_always_empty(self, tmp_path: Path) -> None:
        parsed = _parse_python("class I: pass\n", tmp_path)
        assert detect_fat_interfaces(parsed) == []
