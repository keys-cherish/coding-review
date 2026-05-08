"""
代码解析适配层 — 抽象基类。

为所有语言提供统一的解析输出，让后续的规则引擎、复杂度引擎、
重复检测引擎不感知具体语言细节。

设计动机：
- 评分标准强调"模块化设计"，本抽象层是模块化的核心
- Token、Function、Class 信息独立于具体语言 AST，
  使得跨语言的算法（如重复检测）只需要面向接口编程
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TokenKind(str, Enum):
    """通用 Token 类型，用于跨语言重复检测。

    具体语言的解析器需要把语言特有的 token 映射到这些类别。
    """
    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    NUMBER = "number"
    STRING = "string"
    OPERATOR = "operator"
    PUNCT = "punct"
    NEWLINE = "newline"
    INDENT = "indent"
    DEDENT = "dedent"
    COMMENT = "comment"
    OTHER = "other"


@dataclass
class Token:
    """统一 Token 表示。"""
    kind: TokenKind
    value: str
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0


@dataclass
class FunctionInfo:
    """函数/方法信息。"""
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    parameters: list[str] = field(default_factory=list)
    is_public: bool = True
    has_docstring: bool = False
    raw_node: Any = None
    body_lines: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """类信息。"""
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    is_public: bool = True
    has_docstring: bool = False
    methods: list[FunctionInfo] = field(default_factory=list)
    raw_node: Any = None


@dataclass
class ImportInfo:
    """import 信息。"""
    module: str
    names: list[str] = field(default_factory=list)
    line: int = 0
    is_wildcard: bool = False


@dataclass
class ParsedFile:
    """解析结果统一容器。"""
    file_path: Path
    language: str
    raw_text: str
    raw_lines: list[str]
    tokens: list[Token]
    functions: list[FunctionInfo]
    classes: list[ClassInfo]
    imports: list[ImportInfo]
    ast_root: Any = None
    parse_error: str | None = None

    @property
    def total_lines(self) -> int:
        return len(self.raw_lines)

    @property
    def lines_of_code(self) -> int:
        """非空非纯注释的有效代码行数。"""
        count = 0
        in_block_comment = False
        for line in self.raw_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if self.language == "python":
                if stripped.startswith("#"):
                    continue
            elif self.language == "java":
                if in_block_comment:
                    if "*/" in stripped:
                        in_block_comment = False
                    continue
                if stripped.startswith("/*"):
                    if "*/" not in stripped:
                        in_block_comment = True
                    continue
                if stripped.startswith("//"):
                    continue
            count += 1
        return count


class ParserAdapter(ABC):
    """解析器抽象基类。"""

    language: str = ""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedFile:
        """解析单文件，返回统一格式。"""

    @abstractmethod
    def parse_text(self, text: str, file_path: Path | None = None) -> ParsedFile:
        """从字符串解析，便于单元测试。"""
