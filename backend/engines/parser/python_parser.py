"""
Python 解析器实现。

基于标准库 `ast` + `tokenize`，零外部依赖。
- ast 提供结构化语义信息（函数/类/导入/控制流）
- tokenize 提供精确到列的 token 流，用于重复检测和空格规则
"""
from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path
from typing import cast

from backend.engines.parser.base import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ParsedFile,
    ParserAdapter,
    Token,
    TokenKind,
)
from backend.utils.file_utils import read_text_safely


# Python 关键字集合
_PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield", "match", "case",
}


# tokenize 类型到统一 TokenKind 的映射
# 注：FSTRING_* 常量是 Python 3.12 新增，对 3.10/3.11 用 getattr 兜底
_TOK_TYPE_MAP = {
    tokenize.NAME: TokenKind.IDENTIFIER,
    tokenize.NUMBER: TokenKind.NUMBER,
    tokenize.STRING: TokenKind.STRING,
    tokenize.OP: TokenKind.OPERATOR,
    tokenize.COMMENT: TokenKind.COMMENT,
    tokenize.NEWLINE: TokenKind.NEWLINE,
    tokenize.NL: TokenKind.NEWLINE,
    tokenize.INDENT: TokenKind.INDENT,
    tokenize.DEDENT: TokenKind.DEDENT,
}
for _name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
    _val = getattr(tokenize, _name, None)
    if _val is not None:
        _TOK_TYPE_MAP[_val] = TokenKind.STRING


class PythonParser(ParserAdapter):
    language = "python"

    def parse(self, file_path: Path) -> ParsedFile:
        text = read_text_safely(file_path)
        return self.parse_text(text, file_path)

    def parse_text(self, text: str, file_path: Path | None = None) -> ParsedFile:
        path = file_path or Path("<string>")
        raw_lines = text.splitlines()

        tokens: list[Token] = []
        ast_root: ast.AST | None = None
        parse_error: str | None = None

        try:
            tokens = self._tokenize(text)
        except tokenize.TokenizeError as e:
            parse_error = f"tokenize error: {e}"
        except IndentationError as e:
            parse_error = f"indentation error: {e}"

        try:
            ast_root = ast.parse(text, filename=str(path))
        except SyntaxError as e:
            parse_error = (parse_error + "; " if parse_error else "") + f"syntax error: {e.msg} at line {e.lineno}"
            ast_root = None

        functions, classes = self._extract_structures(ast_root)
        imports = self._extract_imports(ast_root)

        return ParsedFile(
            file_path=path,
            language=self.language,
            raw_text=text,
            raw_lines=raw_lines,
            tokens=tokens,
            functions=functions,
            classes=classes,
            imports=imports,
            ast_root=ast_root,
            parse_error=parse_error,
        )

    @staticmethod
    def _tokenize(text: str) -> list[Token]:
        result: list[Token] = []
        try:
            stream = tokenize.generate_tokens(io.StringIO(text).readline)
            for tok in stream:
                if tok.type in (tokenize.ENCODING, tokenize.ENDMARKER):
                    continue
                kind = _TOK_TYPE_MAP.get(tok.type, TokenKind.OTHER)
                if kind is TokenKind.IDENTIFIER and tok.string in _PY_KEYWORDS:
                    kind = TokenKind.KEYWORD
                result.append(Token(
                    kind=kind,
                    value=tok.string,
                    line=tok.start[0],
                    column=tok.start[1],
                    end_line=tok.end[0],
                    end_column=tok.end[1],
                ))
        except (tokenize.TokenizeError, IndentationError):
            # 部分语法错误下能拿到的 token 仍然返回
            pass
        return result

    def _extract_structures(
        self, root: ast.AST | None
    ) -> tuple[list[FunctionInfo], list[ClassInfo]]:
        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        if root is None:
            return functions, classes

        def visit(node: ast.AST, qualifier: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{qualifier}.{child.name}" if qualifier else child.name
                    info = FunctionInfo(
                        name=child.name,
                        qualified_name=qname,
                        start_line=child.lineno,
                        end_line=getattr(child, "end_lineno", child.lineno) or child.lineno,
                        parameters=[a.arg for a in child.args.args],
                        is_public=not child.name.startswith("_"),
                        has_docstring=ast.get_docstring(child) is not None,
                        raw_node=child,
                    )
                    functions.append(info)
                    visit(child, qname)
                elif isinstance(child, ast.ClassDef):
                    qname = f"{qualifier}.{child.name}" if qualifier else child.name
                    cinfo = ClassInfo(
                        name=child.name,
                        qualified_name=qname,
                        start_line=child.lineno,
                        end_line=getattr(child, "end_lineno", child.lineno) or child.lineno,
                        is_public=not child.name.startswith("_"),
                        has_docstring=ast.get_docstring(child) is not None,
                        raw_node=child,
                    )
                    classes.append(cinfo)
                    visit(child, qname)
                else:
                    visit(child, qualifier)

        visit(cast(ast.AST, root), "")
        return functions, classes

    @staticmethod
    def _extract_imports(root: ast.AST | None) -> list[ImportInfo]:
        out: list[ImportInfo] = []
        if root is None:
            return out
        for node in ast.walk(root):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    out.append(ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        line=node.lineno,
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.name for a in node.names]
                out.append(ImportInfo(
                    module=module,
                    names=names,
                    line=node.lineno,
                    is_wildcard="*" in names,
                ))
        return out
