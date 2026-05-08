"""
解析器工厂与导出。
"""
from __future__ import annotations

from pathlib import Path

from backend.engines.parser.base import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ParsedFile,
    ParserAdapter,
    Token,
    TokenKind,
)
from backend.engines.parser.java_parser import JavaParser
from backend.engines.parser.python_parser import PythonParser

_PARSERS: dict[str, type[ParserAdapter]] = {
    "python": PythonParser,
    "java": JavaParser,
}


def get_parser(language: str) -> ParserAdapter:
    """根据语言名取得解析器实例。"""
    cls = _PARSERS.get(language.lower())
    if cls is None:
        raise ValueError(f"不支持的语言: {language}")
    return cls()


def parse_file(file_path: Path, language: str | None = None) -> ParsedFile:
    """根据扩展名自动选择解析器解析文件。"""
    if language is None:
        if file_path.suffix == ".py":
            language = "python"
        elif file_path.suffix == ".java":
            language = "java"
        else:
            raise ValueError(f"无法识别扩展名: {file_path.suffix}")
    return get_parser(language).parse(file_path)


__all__ = [
    "ClassInfo",
    "FunctionInfo",
    "ImportInfo",
    "JavaParser",
    "ParsedFile",
    "ParserAdapter",
    "PythonParser",
    "Token",
    "TokenKind",
    "get_parser",
    "parse_file",
]
