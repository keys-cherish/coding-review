"""Python / Java 解析器单元测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.engines.parser import get_parser, parse_file
from backend.engines.parser.base import TokenKind


class TestPythonParser:

    def test_clean_file_parses(self, py_fixture_dir: Path) -> None:
        f = parse_file(py_fixture_dir / "clean.py")
        assert f.parse_error is None
        assert f.language == "python"
        assert len(f.functions) >= 2
        names = {fn.name for fn in f.functions}
        assert {"add", "is_even"}.issubset(names)
        assert any(c.name == "Calculator" for c in f.classes)

    def test_token_stream_kinds(self, py_fixture_dir: Path) -> None:
        f = parse_file(py_fixture_dir / "clean.py")
        kinds = {t.kind for t in f.tokens}
        assert TokenKind.IDENTIFIER in kinds
        assert TokenKind.OPERATOR in kinds
        # 关键字会被映射到 KEYWORD
        keyword_tokens = [t for t in f.tokens if t.kind == TokenKind.KEYWORD]
        assert any(t.value == "def" for t in keyword_tokens)
        assert any(t.value == "return" for t in keyword_tokens)

    def test_function_has_docstring_flag(self, py_fixture_dir: Path) -> None:
        f = parse_file(py_fixture_dir / "clean.py")
        add = next(fn for fn in f.functions if fn.name == "add")
        assert add.has_docstring is True

    def test_messy_file_returns_funcs(self, py_fixture_dir: Path) -> None:
        f = parse_file(py_fixture_dir / "messy.py")
        names = {fn.name for fn in f.functions}
        assert "BadFunctionName" in names
        assert "duplicate_block_a" in names

    def test_parse_text_smoke(self) -> None:
        parser = get_parser("python")
        f = parser.parse_text("x = 1\n", file_path=Path("inline.py"))
        assert f.parse_error is None
        assert "x" in f.raw_text

    def test_lines_of_code_counts_correctly(self) -> None:
        parser = get_parser("python")
        f = parser.parse_text(
            "# 注释\n\n"
            "def f():\n"
            "    return 1\n",
            file_path=Path("loc.py"),
        )
        # 仅 def 与 return 是有效代码
        assert f.lines_of_code == 2

    def test_unsupported_language(self) -> None:
        with pytest.raises(ValueError):
            get_parser("ruby")


class TestJavaParser:

    def test_messy_java_parses(self, java_fixture_dir: Path) -> None:
        f = parse_file(java_fixture_dir / "Messy.java")
        # javalang 解析失败时会写入 parse_error，但常规结构应能识别
        assert f.language == "java"
        # 即便部分 token 失败，至少类应该被发现
        assert len(f.classes) >= 1

    def test_java_function_extraction(self, java_fixture_dir: Path) -> None:
        f = parse_file(java_fixture_dir / "Messy.java")
        all_methods = []
        for c in f.classes:
            all_methods.extend(c.methods)
        names = {m.name for m in all_methods}
        assert "Bad_Method_Name" in names or any("duplicate" in n for n in names)
