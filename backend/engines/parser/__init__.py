"""
解析器工厂与导出。

策略
----
1. Python / Java 默认走原生 AST 解析器（javalang / ast），语义最精准。
2. 其他语言通过 tree-sitter 通用解析器覆盖，零工具链依赖。
3. tree-sitter 未安装时降级为"仅 Python + Java"。
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
from backend.engines.parser.config_parser import ConfigParser
from backend.engines.parser.java_parser import JavaParser
from backend.engines.parser.python_parser import PythonParser

try:
    from backend.engines.parser.tree_sitter_parser import (
        EXT_TO_LANG as _TS_EXT_TO_LANG,
        LANG_SPECS as _TS_LANG_SPECS,
        TreeSitterParser,
    )
    _TS_READY = True
except Exception:  # pragma: no cover
    _TS_EXT_TO_LANG = {}
    _TS_LANG_SPECS = {}
    TreeSitterParser = None  # type: ignore[assignment]
    _TS_READY = False


# 原生解析器优先（语义精度最高）
_NATIVE_PARSERS: dict[str, type[ParserAdapter]] = {
    "python": PythonParser,
    "java": JavaParser,
    "config": ConfigParser,
}

# 扩展名 → 语言。原生覆盖 + Tree-sitter 补全（Python/Java 也可以被 tree-sitter 走，但默认走原生）
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".java": "java",
    ".json": "config",
    ".yaml": "config",
    ".yml": "config",
    ".toml": "config",
    ".ini": "config",
    ".cfg": "config",
    ".conf": "config",
    ".properties": "config",
    ".env": "config",
}
if _TS_READY:
    for _ext, _lang in _TS_EXT_TO_LANG.items():
        _EXT_TO_LANG.setdefault(_ext, _lang)


def supported_languages() -> list[str]:
    """返回当前环境可解析的语言清单（用于接口/前端展示）。"""
    langs = set(_NATIVE_PARSERS.keys())
    if _TS_READY:
        langs.update(_TS_LANG_SPECS.keys())
    return sorted(langs)


def get_parser(language: str) -> ParserAdapter:
    """根据语言名取得解析器实例。

    优先原生解析器，其次 tree-sitter。
    """
    key = language.lower()
    cls = _NATIVE_PARSERS.get(key)
    if cls is not None:
        return cls()
    if _TS_READY and key in _TS_LANG_SPECS:
        return TreeSitterParser(key)  # type: ignore[operator]
    raise ValueError(
        f"不支持的语言: {language}。已支持: {', '.join(supported_languages())}"
    )


def parse_file(file_path: Path, language: str | None = None) -> ParsedFile:
    """根据扩展名自动选择解析器解析文件。"""
    if language is None:
        language = _EXT_TO_LANG.get(file_path.suffix.lower()) or _EXT_TO_LANG.get(file_path.name.lower())
        if language is None:
            raise ValueError(f"无法识别扩展名: {file_path.suffix}")
    return get_parser(language).parse(file_path)


__all__ = [
    "ClassInfo",
    "FunctionInfo",
    "ImportInfo",
    "ConfigParser",
    "JavaParser",
    "ParsedFile",
    "ParserAdapter",
    "PythonParser",
    "Token",
    "TokenKind",
    "TreeSitterParser",
    "get_parser",
    "parse_file",
    "supported_languages",
]
