"""
Tree-sitter 通用解析适配器。

动机
----
原有 python_parser / java_parser 基于各自语言的原生 AST 包（ast / javalang），
要继续扩展到 JS/TS/Go/Rust/C/C++/C#/Ruby/PHP/Kotlin/Swift 成本极高。
Tree-sitter 具备三个关键红利：

1. **错误容错**：即使源文件有语法错误或缺依赖，仍能产出带 ERROR 节点的 AST，
   这正是 CodeGuard 的核心场景（用户直接丢 ZIP，无构建环境）。
2. **增量解析**：后续可支持编辑器场景的增量分析。
3. **查询统一**：一套 walker 适配所有语言，新增语言只要补一条 LANG_SPEC。

本解析器输出与 ParserAdapter 完全一致的 ParsedFile，
让 duplication / complexity / naming 等下游引擎无感知切换。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.engines.parser.base import (
    ClassInfo,
    FunctionInfo,
    ImportInfo,
    ParsedFile,
    ParserAdapter,
    Token,
    TokenKind,
)

try:
    from tree_sitter_language_pack import get_parser as _ts_get_parser
    _TS_AVAILABLE = True
    _TS_IMPORT_ERROR: str | None = None
except Exception as e:  # pragma: no cover
    _TS_AVAILABLE = False
    _TS_IMPORT_ERROR = str(e)


# ---------------------------------------------------------------------------
# 语言能力表
#
# 说明：
#   每种语言只需声明"这些节点类型是函数/类/import"即可。
#   因此新增语言支持的成本 ≈ 写 3 行配置，不用写 AST 转换代码。
#
#   name_fields 是常见的"名字字段"集合，遍历取第一个非空。
#   docstring_probe 用于启发式判断函数是否带文档注释。
# ---------------------------------------------------------------------------

class LangSpec:
    __slots__ = (
        "language",
        "extensions",
        "function_nodes",
        "method_nodes",
        "class_nodes",
        "import_nodes",
        "name_fields",
        "comment_nodes",
        "docstring_probe",
    )

    def __init__(
        self,
        language: str,
        extensions: tuple[str, ...],
        function_nodes: tuple[str, ...],
        method_nodes: tuple[str, ...] = (),
        class_nodes: tuple[str, ...] = (),
        import_nodes: tuple[str, ...] = (),
        name_fields: tuple[str, ...] = ("name",),
        comment_nodes: tuple[str, ...] = ("comment", "line_comment", "block_comment"),
        docstring_probe: tuple[str, ...] = ("string", "string_literal"),
    ) -> None:
        self.language = language
        self.extensions = extensions
        self.function_nodes = function_nodes
        self.method_nodes = method_nodes
        self.class_nodes = class_nodes
        self.import_nodes = import_nodes
        self.name_fields = name_fields
        self.comment_nodes = comment_nodes
        self.docstring_probe = docstring_probe


LANG_SPECS: dict[str, LangSpec] = {
    # 已有 python_parser / java_parser 负责主流程；
    # 此处保留 spec 便于以 tree-sitter 做交叉验证或 fallback。
    "python": LangSpec(
        language="python",
        extensions=(".py", ".pyw"),
        function_nodes=("function_definition",),
        class_nodes=("class_definition",),
        import_nodes=("import_statement", "import_from_statement"),
        docstring_probe=("string", "expression_statement"),
    ),
    "java": LangSpec(
        language="java",
        extensions=(".java",),
        function_nodes=(),
        method_nodes=("method_declaration", "constructor_declaration"),
        class_nodes=("class_declaration", "interface_declaration", "enum_declaration", "record_declaration"),
        import_nodes=("import_declaration",),
    ),

    # Tree-sitter 新覆盖的语言
    "javascript": LangSpec(
        language="javascript",
        extensions=(".js", ".jsx", ".mjs", ".cjs"),
        function_nodes=("function_declaration", "function", "arrow_function", "generator_function_declaration"),
        method_nodes=("method_definition",),
        class_nodes=("class_declaration",),
        import_nodes=("import_statement",),
    ),
    "typescript": LangSpec(
        language="typescript",
        extensions=(".ts",),
        function_nodes=("function_declaration", "function", "arrow_function", "generator_function_declaration"),
        method_nodes=("method_definition", "method_signature"),
        class_nodes=("class_declaration", "interface_declaration", "type_alias_declaration"),
        import_nodes=("import_statement",),
    ),
    "tsx": LangSpec(
        language="tsx",
        extensions=(".tsx",),
        function_nodes=("function_declaration", "function", "arrow_function"),
        method_nodes=("method_definition", "method_signature"),
        class_nodes=("class_declaration", "interface_declaration", "type_alias_declaration"),
        import_nodes=("import_statement",),
    ),
    "go": LangSpec(
        language="go",
        extensions=(".go",),
        function_nodes=("function_declaration",),
        method_nodes=("method_declaration",),
        class_nodes=("type_declaration",),
        import_nodes=("import_declaration",),
    ),
    "rust": LangSpec(
        language="rust",
        extensions=(".rs",),
        function_nodes=("function_item",),
        class_nodes=("struct_item", "enum_item", "trait_item", "impl_item"),
        import_nodes=("use_declaration",),
    ),
    "c": LangSpec(
        language="c",
        extensions=(".c", ".h"),
        function_nodes=("function_definition",),
        class_nodes=("struct_specifier", "union_specifier", "enum_specifier"),
        import_nodes=("preproc_include",),
        name_fields=("name", "declarator"),
    ),
    "cpp": LangSpec(
        language="cpp",
        extensions=(".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
        function_nodes=("function_definition",),
        method_nodes=("function_definition",),
        class_nodes=("class_specifier", "struct_specifier", "union_specifier"),
        import_nodes=("preproc_include",),
        name_fields=("name", "declarator"),
    ),
    "csharp": LangSpec(
        language="csharp",
        extensions=(".cs",),
        function_nodes=("local_function_statement",),
        method_nodes=("method_declaration", "constructor_declaration"),
        class_nodes=("class_declaration", "struct_declaration", "interface_declaration", "record_declaration"),
        import_nodes=("using_directive",),
    ),
    "ruby": LangSpec(
        language="ruby",
        extensions=(".rb",),
        function_nodes=("method", "singleton_method"),
        class_nodes=("class", "module"),
        import_nodes=("call",),  # require/require_relative 是 method call
    ),
    "php": LangSpec(
        language="php",
        extensions=(".php",),
        function_nodes=("function_definition",),
        method_nodes=("method_declaration",),
        class_nodes=("class_declaration", "interface_declaration", "trait_declaration"),
        import_nodes=("namespace_use_declaration",),
    ),
    "kotlin": LangSpec(
        language="kotlin",
        extensions=(".kt", ".kts"),
        function_nodes=("function_declaration",),
        class_nodes=("class_declaration", "object_declaration"),
        import_nodes=("import_header",),
    ),
    "swift": LangSpec(
        language="swift",
        extensions=(".swift",),
        function_nodes=("function_declaration",),
        class_nodes=("class_declaration", "protocol_declaration", "enum_declaration"),
        import_nodes=("import_declaration",),
    ),
}


# 扩展名 → 语言 反查表（用于按文件自动挑选语言）
EXT_TO_LANG: dict[str, str] = {}
for _lang, _spec in LANG_SPECS.items():
    for _ext in _spec.extensions:
        EXT_TO_LANG[_ext] = _lang


def language_of(file_path: Path) -> str | None:
    """根据扩展名识别 tree-sitter 支持的语言，找不到返回 None。"""
    return EXT_TO_LANG.get(file_path.suffix.lower())


# ---------------------------------------------------------------------------
# Token kind 启发式映射
#
# Tree-sitter 各语言 grammar 节点类型繁杂，但通过前缀/后缀大体可以归类。
# 下游重复检测只需要 kind 稳定，不要求绝对精准。
# ---------------------------------------------------------------------------

_STRING_HINTS = ("string", "interpreted_string", "raw_string", "char_literal", "heredoc")
_NUMBER_HINTS = ("integer", "float", "number", "decimal", "hex", "binary", "octal")
_COMMENT_HINTS = ("comment",)
_OPERATOR_CHARS = set("+-*/%=<>!&|^~?:")
_PUNCT_CHARS = set("()[]{},;.")


def _classify_token(node_type: str, text: str) -> TokenKind:
    """根据节点类型 + 字面量内容推断 TokenKind。"""
    lt = node_type.lower()
    if any(h in lt for h in _COMMENT_HINTS):
        return TokenKind.COMMENT
    if any(h in lt for h in _STRING_HINTS):
        return TokenKind.STRING
    if any(h in lt for h in _NUMBER_HINTS):
        return TokenKind.NUMBER
    if lt == "identifier" or lt.endswith("_identifier"):
        return TokenKind.IDENTIFIER

    # tree-sitter 对关键字通常用文本自身作为 type，长度较短且全字母。
    if text and text.isalpha() and text.islower() and len(text) <= 20:
        return TokenKind.KEYWORD

    if text and len(text) <= 3 and all(c in _OPERATOR_CHARS for c in text):
        return TokenKind.OPERATOR
    if text and len(text) <= 2 and all(c in _PUNCT_CHARS for c in text):
        return TokenKind.PUNCT
    return TokenKind.OTHER


# ---------------------------------------------------------------------------
# 解析器本体
# ---------------------------------------------------------------------------

class TreeSitterParser(ParserAdapter):
    """基于 tree-sitter 的多语言通用解析器。

    用法：
        parser = TreeSitterParser("javascript")
        pf = parser.parse(Path("app.js"))
    """

    def __init__(self, language: str) -> None:
        if not _TS_AVAILABLE:
            raise RuntimeError(
                "tree-sitter 未安装或加载失败。请执行：\n"
                "  pip install tree-sitter tree-sitter-language-pack\n"
                f"原始错误: {_TS_IMPORT_ERROR}"
            )
        spec = LANG_SPECS.get(language.lower())
        if spec is None:
            raise ValueError(f"tree-sitter 未提供该语言的映射表: {language}")
        self.language = spec.language
        self._spec = spec
        self._parser = _ts_get_parser(spec.language)

    # ---- 公共入口 -------------------------------------------------------

    def parse(self, file_path: Path) -> ParsedFile:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return self._parse_source(text, file_path)

    def parse_text(self, text: str, file_path: Path | None = None) -> ParsedFile:
        return self._parse_source(text, file_path or Path(f"<memory>.{self._spec.extensions[0].lstrip('.')}"))

    # ---- 核心 ----------------------------------------------------------

    def _parse_source(self, text: str, file_path: Path) -> ParsedFile:
        source_bytes = text.encode("utf-8", errors="replace")
        raw_lines = text.splitlines()

        parse_error: str | None = None
        try:
            tree = self._parser.parse(source_bytes)
            root = tree.root_node
            if root.has_error:
                # tree-sitter 仍会返回树，只记录标志，不抛异常
                parse_error = "存在语法错误节点（已容错解析）"
        except Exception as e:  # pragma: no cover
            parse_error = f"tree-sitter 解析失败: {e}"
            return ParsedFile(
                file_path=file_path,
                language=self.language,
                raw_text=text,
                raw_lines=raw_lines,
                tokens=[],
                functions=[],
                classes=[],
                imports=[],
                ast_root=None,
                parse_error=parse_error,
            )

        tokens = self._extract_tokens(root, source_bytes)
        functions, classes = self._extract_structural(root, source_bytes, raw_lines)
        imports = self._extract_imports(root, source_bytes)

        return ParsedFile(
            file_path=file_path,
            language=self.language,
            raw_text=text,
            raw_lines=raw_lines,
            tokens=tokens,
            functions=functions,
            classes=classes,
            imports=imports,
            ast_root=root,
            parse_error=parse_error,
        )

    # ---- 工具：字节区间取字符串 ----------------------------------------

    @staticmethod
    def _slice(node: Any, src: bytes) -> str:
        try:
            return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _find_name(self, node: Any, src: bytes) -> str:
        """在 node 的子节点里找名字字段；找不到则扫第一层 identifier。"""
        for f in self._spec.name_fields:
            child = node.child_by_field_name(f)
            if child is not None:
                txt = self._slice(child, src).strip()
                if txt:
                    return txt
        for c in node.children:
            if c.type == "identifier" or c.type.endswith("_identifier"):
                txt = self._slice(c, src).strip()
                if txt:
                    return txt
        return "<anonymous>"

    # ---- Token 抽取 ----------------------------------------------------

    def _extract_tokens(self, root: Any, src: bytes) -> list[Token]:
        """深度优先遍历叶子节点生成 Token 列表。"""
        tokens: list[Token] = []
        stack: list[Any] = [root]
        while stack:
            node = stack.pop()
            # 仅对叶子或字面量/注释节点出 token，避免把非终结符也塞进去
            if node.child_count == 0 or node.type.lower() in _COMMENT_HINTS or \
                    any(h in node.type.lower() for h in _STRING_HINTS + _NUMBER_HINTS):
                text = self._slice(node, src)
                if text and not text.isspace():
                    kind = _classify_token(node.type, text)
                    start = node.start_point  # (row, col) 0-based
                    end = node.end_point
                    tokens.append(Token(
                        kind=kind,
                        value=text,
                        line=start[0] + 1,
                        column=start[1],
                        end_line=end[0] + 1,
                        end_column=end[1],
                    ))
                continue
            # 非叶子继续展开
            for child in node.children:
                stack.append(child)
        # 栈序是反的，按起始行列排个序
        tokens.sort(key=lambda t: (t.line, t.column))
        return tokens

    # ---- 函数 / 类 抽取 ------------------------------------------------

    def _extract_structural(
        self,
        root: Any,
        src: bytes,
        raw_lines: list[str],
    ) -> tuple[list[FunctionInfo], list[ClassInfo]]:
        """一次遍历同时抓函数与类，维护父类命名空间构造 qualified_name。"""
        fn_types = set(self._spec.function_nodes + self._spec.method_nodes)
        cls_types = set(self._spec.class_nodes)

        functions: list[FunctionInfo] = []
        classes: list[ClassInfo] = []

        def walk(node: Any, class_stack: list[ClassInfo]) -> None:
            if node.type in cls_types:
                name = self._find_name(node, src)
                qual = ".".join([c.name for c in class_stack] + [name])
                cls_info = ClassInfo(
                    name=name,
                    qualified_name=qual,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    has_docstring=self._has_docstring(node, src),
                    raw_node=node,
                )
                classes.append(cls_info)
                class_stack.append(cls_info)
                for c in node.children:
                    walk(c, class_stack)
                class_stack.pop()
                return

            if node.type in fn_types:
                name = self._find_name(node, src)
                qual = ".".join([c.name for c in class_stack] + [name])
                fn = FunctionInfo(
                    name=name,
                    qualified_name=qual,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    parameters=self._extract_parameters(node, src),
                    is_public=not name.startswith("_"),
                    has_docstring=self._has_docstring(node, src),
                    raw_node=node,
                    body_lines=raw_lines[node.start_point[0]:node.end_point[0] + 1],
                )
                functions.append(fn)
                if class_stack:
                    class_stack[-1].methods.append(fn)
                # 允许嵌套函数继续扫描（Python / JS 闭包）
                for c in node.children:
                    walk(c, class_stack)
                return

            for c in node.children:
                walk(c, class_stack)

        walk(root, [])
        return functions, classes

    def _extract_parameters(self, fn_node: Any, src: bytes) -> list[str]:
        """粗略抓参数名，不要求完全精准（复杂度引擎不用）。"""
        params_node = fn_node.child_by_field_name("parameters") or \
                      fn_node.child_by_field_name("formal_parameters")
        if params_node is None:
            # 退一步：找第一个 parameters-like 子节点
            for c in fn_node.children:
                if "parameter" in c.type:
                    params_node = c
                    break
        if params_node is None:
            return []
        out: list[str] = []
        for c in params_node.children:
            if c.type in ("identifier", "simple_parameter", "required_parameter",
                           "optional_parameter", "typed_parameter", "default_parameter",
                           "parameter_declaration"):
                ident = None
                for cc in c.children:
                    if cc.type == "identifier" or cc.type.endswith("_identifier"):
                        ident = cc
                        break
                text = self._slice(ident or c, src).strip()
                if text and text not in {",", "(", ")"}:
                    out.append(text)
        return out

    def _has_docstring(self, node: Any, src: bytes) -> bool:
        """启发式：函数/类首个子语句是否为字符串/注释。"""
        body = node.child_by_field_name("body")
        candidates = list(body.children) if body else list(node.children)
        for c in candidates:
            if c.type in self._spec.docstring_probe:
                txt = self._slice(c, src).strip()
                if txt:
                    return True
            if c.type not in self._spec.comment_nodes and c.is_named:
                # 已经碰到非注释语句，不再是 docstring 位置
                break
        return False

    # ---- import 抽取 ---------------------------------------------------

    def _extract_imports(self, root: Any, src: bytes) -> list[ImportInfo]:
        import_types = set(self._spec.import_nodes)
        if not import_types:
            return []

        out: list[ImportInfo] = []
        stack: list[Any] = [root]
        while stack:
            node = stack.pop()
            if node.type in import_types:
                raw = self._slice(node, src).strip()
                out.append(ImportInfo(
                    module=raw.splitlines()[0][:200],  # 避免异常超长行
                    names=[],
                    line=node.start_point[0] + 1,
                    is_wildcard="*" in raw,
                ))
                continue
            for c in node.children:
                stack.append(c)
        out.sort(key=lambda i: i.line)
        return out


__all__ = [
    "TreeSitterParser",
    "LANG_SPECS",
    "EXT_TO_LANG",
    "language_of",
]
