"""配置文件轻量解析器。"""
from __future__ import annotations

import configparser
import json
import re
import tomllib
from pathlib import Path

from backend.engines.parser.base import ParsedFile, ParserAdapter, Token, TokenKind
from backend.utils.file_utils import read_text_safely


class ConfigParser(ParserAdapter):
    language = "config"

    def parse(self, file_path: Path) -> ParsedFile:
        return self.parse_text(read_text_safely(file_path), file_path)

    def parse_text(self, text: str, file_path: Path | None = None) -> ParsedFile:
        path = file_path or Path("<config>")
        raw_lines = text.splitlines()
        parse_error = _validate_config(path, text)
        return ParsedFile(
            file_path=path,
            language=self.language,
            raw_text=text,
            raw_lines=raw_lines,
            tokens=_tokenize(raw_lines),
            functions=[],
            classes=[],
            imports=[],
            ast_root=None,
            parse_error=parse_error,
        )


def _validate_config(path: Path, text: str) -> str | None:
    suffix = path.suffix.lower()
    name = path.name.lower()
    stripped = text.strip()
    if not stripped:
        return None

    try:
        if suffix == ".json" or name.endswith(".jsonc"):
            json.loads(_strip_json_comments(text))
        elif suffix == ".toml":
            tomllib.loads(text)
        elif suffix in {".ini", ".cfg", ".conf"}:
            parser = configparser.ConfigParser()
            parser.read_string(text if re.search(r"^\s*\[.+?\]", text, re.M) else "[default]\n" + text)
    except Exception as exc:
        return str(exc)
    return None


def _strip_json_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        lines.append(re.sub(r"\s+//.*$", "", line))
    return "\n".join(lines)


def _tokenize(lines: list[str]) -> list[Token]:
    tokens: list[Token] = []
    for line_no, line in enumerate(lines, start=1):
        for match in re.finditer(r"[A-Za-z_][\w.-]*|\d+(?:\.\d+)?|[{}\[\](),:=]|\"[^\"]*\"|'[^']*'", line):
            value = match.group(0)
            if value[0].isalpha() or value[0] == "_":
                kind = TokenKind.IDENTIFIER
            elif value[0].isdigit():
                kind = TokenKind.NUMBER
            elif value[0] in {'\"', "'"}:
                kind = TokenKind.STRING
            else:
                kind = TokenKind.PUNCT
            tokens.append(Token(kind=kind, value=value, line=line_no, column=match.start()))
    return tokens
