"""
Java 解析器实现。

基于纯 Python 库 `javalang`，无需 JVM。
javalang 提供完整的 Java 语法树和 token 流，覆盖 Java 7+ 语法。
对 Java 14+ 的部分新语法（switch expression / record / sealed）会降级处理。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import javalang
from javalang import tokenizer as jtok
from javalang.tree import (
    ClassDeclaration,
    ConstructorDeclaration,
    InterfaceDeclaration,
    MethodDeclaration,
)

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


# javalang token 类型映射
_JTOK_MAP: dict[type, TokenKind] = {
    jtok.Keyword: TokenKind.KEYWORD,
    jtok.Modifier: TokenKind.KEYWORD,
    jtok.BasicType: TokenKind.KEYWORD,
    jtok.Boolean: TokenKind.KEYWORD,
    jtok.Null: TokenKind.KEYWORD,
    jtok.Identifier: TokenKind.IDENTIFIER,
    jtok.Integer: TokenKind.NUMBER,
    jtok.DecimalInteger: TokenKind.NUMBER,
    jtok.OctalInteger: TokenKind.NUMBER,
    jtok.HexInteger: TokenKind.NUMBER,
    jtok.BinaryInteger: TokenKind.NUMBER,
    jtok.FloatingPoint: TokenKind.NUMBER,
    jtok.DecimalFloatingPoint: TokenKind.NUMBER,
    jtok.HexFloatingPoint: TokenKind.NUMBER,
    jtok.String: TokenKind.STRING,
    jtok.Character: TokenKind.STRING,
    jtok.Operator: TokenKind.OPERATOR,
    jtok.Separator: TokenKind.PUNCT,
    jtok.Annotation: TokenKind.OTHER,
}


_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*[\s\S]*?\*/")


class JavaParser(ParserAdapter):
    language = "java"

    def parse(self, file_path: Path) -> ParsedFile:
        text = read_text_safely(file_path)
        return self.parse_text(text, file_path)

    def parse_text(self, text: str, file_path: Path | None = None) -> ParsedFile:
        path = file_path or Path("<string>")
        raw_lines = text.splitlines()

        tokens = self._tokenize(text)
        ast_root: Any = None
        parse_error: str | None = None
        try:
            ast_root = javalang.parse.parse(text)
        except javalang.parser.JavaSyntaxError as e:
            parse_error = f"syntax error: {e.description} at line {e.at if e.at else '?'}"
        except javalang.tokenizer.LexerError as e:
            parse_error = f"lexer error: {e}"
        except Exception as e:
            parse_error = f"parse failed: {type(e).__name__}: {e}"

        functions, classes = self._extract_structures(ast_root, raw_lines)
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
        out: list[Token] = []
        # 提取注释（javalang 默认丢弃注释，自己用正则补回）
        for m in _LINE_COMMENT.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            out.append(Token(TokenKind.COMMENT, m.group(), line=line, column=0))
        for m in _BLOCK_COMMENT.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            out.append(Token(TokenKind.COMMENT, m.group(), line=line, column=0))

        try:
            for jt in javalang.tokenizer.tokenize(text):
                kind = _JTOK_MAP.get(type(jt), TokenKind.OTHER)
                pos = jt.position if jt.position else (0, 0)
                out.append(Token(
                    kind=kind,
                    value=jt.value,
                    line=pos[0],
                    column=pos[1],
                ))
        except javalang.tokenizer.LexerError:
            pass

        out.sort(key=lambda t: (t.line, t.column))
        return out

    def _extract_structures(
        self, ast_root: Any, raw_lines: list[str]
    ) -> tuple[list[FunctionInfo], list[ClassInfo]]:
        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        if ast_root is None:
            return functions, classes

        # 遍历所有 ClassDeclaration / InterfaceDeclaration
        # 注：javalang.filter 不支持 tuple，需分别调用后合并
        type_iter = []
        for cls in (ClassDeclaration, InterfaceDeclaration):
            for path, node in ast_root.filter(cls):
                type_iter.append((path, node))
        for path, node in type_iter:
            cname = node.name
            qname = self._qualify(path, cname)
            start_line = node.position.line if node.position else 1
            end_line = self._estimate_end_line(node, raw_lines, start_line)

            cinfo = ClassInfo(
                name=cname,
                qualified_name=qname,
                start_line=start_line,
                end_line=end_line,
                is_public="public" in (node.modifiers or set()),
                has_docstring=self._has_javadoc(node, raw_lines),
                raw_node=node,
            )
            classes.append(cinfo)

            # 收集类内方法
            for member in (node.body or []):
                if isinstance(member, (MethodDeclaration, ConstructorDeclaration)):
                    mstart = member.position.line if member.position else start_line
                    mend = self._estimate_end_line(member, raw_lines, mstart)
                    fname = member.name if isinstance(member, MethodDeclaration) else cname
                    fqname = f"{qname}.{fname}"
                    info = FunctionInfo(
                        name=fname,
                        qualified_name=fqname,
                        start_line=mstart,
                        end_line=mend,
                        parameters=[p.name for p in (member.parameters or [])],
                        is_public="public" in (member.modifiers or set()),
                        has_docstring=self._has_javadoc(member, raw_lines),
                        raw_node=member,
                    )
                    functions.append(info)
                    cinfo.methods.append(info)

        return functions, classes

    @staticmethod
    def _qualify(path, name: str) -> str:
        parts: list[str] = []
        for ancestor in path:
            if isinstance(ancestor, (ClassDeclaration, InterfaceDeclaration)):
                parts.append(ancestor.name)
        parts.append(name)
        return ".".join(parts)

    @staticmethod
    def _has_javadoc(node, raw_lines: list[str]) -> bool:
        if not node.position:
            return False
        line = node.position.line
        # 向上找最多 30 行
        for i in range(line - 2, max(line - 32, -1), -1):
            if i < 0 or i >= len(raw_lines):
                break
            stripped = raw_lines[i].strip()
            if not stripped:
                continue
            if stripped.endswith("*/"):
                # 找开始
                for j in range(i, max(i - 50, -1), -1):
                    if "/**" in raw_lines[j]:
                        return True
                return False
            return False
        return False

    @staticmethod
    def _estimate_end_line(node, raw_lines: list[str], start_line: int) -> int:
        """通过括号配对估算结束行。"""
        if start_line < 1 or start_line > len(raw_lines):
            return start_line
        depth = 0
        started = False
        for idx in range(start_line - 1, len(raw_lines)):
            line = raw_lines[idx]
            for ch in line:
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1
                    if started and depth <= 0:
                        return idx + 1
            # 字段/抽象方法：以 ; 结尾且未进入块
            if not started and ";" in line:
                return idx + 1
        return len(raw_lines)

    @staticmethod
    def _extract_imports(ast_root: Any) -> list[ImportInfo]:
        out: list[ImportInfo] = []
        if ast_root is None:
            return out
        for imp in (ast_root.imports or []):
            line = imp.position.line if imp.position else 0
            is_wild = bool(imp.wildcard)
            module = imp.path
            out.append(ImportInfo(
                module=module,
                names=["*"] if is_wild else [module.split(".")[-1]],
                line=line,
                is_wildcard=is_wild,
            ))
        return out
