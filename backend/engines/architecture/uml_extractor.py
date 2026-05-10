"""
UML 类图提取器。

从 ParsedFile 抽出 class / field / method / 继承关系，
并渲染 Mermaid 与 PlantUML 两种 DSL。
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from backend.engines.parser.base import ParsedFile


@dataclass
class UMLField:
    name: str
    type: str = ""
    visibility: str = "+"  # + public / - private / # protected


@dataclass
class UMLMethod:
    name: str
    params: list[str] = field(default_factory=list)
    returns: str = ""
    visibility: str = "+"
    is_static: bool = False


@dataclass
class UMLClass:
    name: str
    file: str
    parents: list[str] = field(default_factory=list)
    fields: list[UMLField] = field(default_factory=list)
    methods: list[UMLMethod] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file": self.file,
            "parents": self.parents,
            "fields": [f.__dict__ for f in self.fields],
            "methods": [m.__dict__ for m in self.methods],
        }


def _python_visibility(name: str) -> str:
    if name.startswith("__") and not name.endswith("__"):
        return "-"
    if name.startswith("_"):
        return "#"
    return "+"


def _extract_python_class(cls_ast: ast.ClassDef, file: str) -> UMLClass:
    uc = UMLClass(name=cls_ast.name, file=file)
    # 父类名
    for base in cls_ast.bases:
        if isinstance(base, ast.Name):
            uc.parents.append(base.id)
        elif isinstance(base, ast.Attribute):
            uc.parents.append(base.attr)

    for node in cls_ast.body:
        # 字段：ClassVar / 属性注解 / self.x 赋值 / __init__ 里的 self.x
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            uc.fields.append(UMLField(
                name=name,
                type=_py_ann_str(node.annotation),
                visibility=_python_visibility(name),
            ))
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    uc.fields.append(UMLField(
                        name=tgt.id,
                        visibility=_python_visibility(tgt.id),
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in node.args.args if a.arg != "self"]
            is_static = any(
                (isinstance(d, ast.Name) and d.id == "staticmethod") or
                (isinstance(d, ast.Attribute) and d.attr == "staticmethod")
                for d in node.decorator_list
            )
            returns = _py_ann_str(node.returns) if node.returns else ""
            uc.methods.append(UMLMethod(
                name=node.name,
                params=params,
                returns=returns,
                visibility=_python_visibility(node.name),
                is_static=is_static,
            ))
            # 从 __init__ 里挖 self.x 字段
            if node.name == "__init__":
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Assign):
                        for t in inner.targets:
                            if (
                                isinstance(t, ast.Attribute)
                                and isinstance(t.value, ast.Name)
                                and t.value.id == "self"
                            ):
                                if not any(f.name == t.attr for f in uc.fields):
                                    uc.fields.append(UMLField(
                                        name=t.attr,
                                        visibility=_python_visibility(t.attr),
                                    ))
    return uc


def _py_ann_str(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        base = _py_ann_str(node.value)
        inner = _py_ann_str(node.slice)
        return f"{base}[{inner}]" if inner else base
    if isinstance(node, ast.Tuple):
        return ", ".join(_py_ann_str(e) for e in node.elts)
    if isinstance(node, ast.Constant):
        return str(node.value)
    return ""


def _extract_java_class(cls_node: Any, file: str) -> UMLClass:
    """javalang 的 ClassDeclaration / InterfaceDeclaration。"""
    uc = UMLClass(name=getattr(cls_node, "name", "?"), file=file)
    ext = getattr(cls_node, "extends", None)
    if ext is not None:
        names = ext if isinstance(ext, list) else [ext]
        for e in names:
            uc.parents.append(getattr(e, "name", str(e)))
    impls = getattr(cls_node, "implements", None) or []
    for i in impls:
        uc.parents.append(getattr(i, "name", str(i)))

    body = getattr(cls_node, "body", []) or []
    for member in body:
        # FieldDeclaration
        if hasattr(member, "declarators") and hasattr(member, "type"):
            type_name = getattr(getattr(member, "type", None), "name", "")
            mods = getattr(member, "modifiers", set()) or set()
            vis = "+" if "public" in mods else ("-" if "private" in mods else "#")
            for d in member.declarators:
                uc.fields.append(UMLField(name=getattr(d, "name", "?"), type=type_name, visibility=vis))
        # MethodDeclaration
        if hasattr(member, "parameters") and hasattr(member, "name"):
            mods = getattr(member, "modifiers", set()) or set()
            vis = "+" if "public" in mods else ("-" if "private" in mods else "#")
            params = [getattr(p, "name", "?") for p in (member.parameters or [])]
            ret_t = getattr(getattr(member, "return_type", None), "name", "") or "void"
            uc.methods.append(UMLMethod(
                name=member.name,
                params=params,
                returns=ret_t,
                visibility=vis,
                is_static="static" in mods,
            ))
    return uc


def extract_uml_classes(parsed_files: list[ParsedFile]) -> list[UMLClass]:
    out: list[UMLClass] = []
    for pf in parsed_files:
        rel = PurePosixPath(str(pf.file_path)).as_posix()
        if pf.language == "python" and pf.ast_root is not None:
            for node in ast.walk(pf.ast_root):
                if isinstance(node, ast.ClassDef):
                    out.append(_extract_python_class(node, rel))
        elif pf.language == "java" and pf.ast_root is not None:
            try:
                for _, tnode in pf.ast_root.filter(type(pf.ast_root).__mro__[0]):
                    pass
            except Exception:
                pass
            # 用 types 属性遍历（javalang CompilationUnit）
            types = getattr(pf.ast_root, "types", []) or []
            for t in types:
                out.append(_extract_java_class(t, rel))
    return out


def render_mermaid_class_diagram(classes: list[UMLClass], max_classes: int = 30) -> str:
    lines = ["classDiagram"]
    shown = classes[:max_classes]
    shown_names = {c.name for c in shown}
    for c in shown:
        lines.append(f"    class {_sanitize(c.name)} {{")
        for f in c.fields[:12]:
            sym = f.visibility or "+"
            type_hint = f": {f.type}" if f.type else ""
            lines.append(f"        {sym}{_sanitize(f.name)}{type_hint}")
        for m in c.methods[:14]:
            sym = m.visibility or "+"
            param_s = ", ".join(m.params)
            ret = f" {m.returns}" if m.returns else ""
            lines.append(f"        {sym}{_sanitize(m.name)}({param_s}){ret}")
        lines.append("    }")
    # 继承关系：父 <|-- 子
    for c in shown:
        for p in c.parents:
            if p in shown_names:
                lines.append(f"    {_sanitize(p)} <|-- {_sanitize(c.name)}")
    if not any(l.startswith("    class") for l in lines):
        lines.append("    class Empty {")
        lines.append("        +noData()")
        lines.append("    }")
    return "\n".join(lines)


def _sanitize(name: str) -> str:
    # Mermaid 不接受特殊字符作为类名
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name) or "Unnamed"


def render_plantuml_class_diagram(classes: list[UMLClass], max_classes: int = 30) -> str:
    lines = ["@startuml"]
    shown = classes[:max_classes]
    shown_names = {c.name for c in shown}
    for c in shown:
        lines.append(f"class {_sanitize(c.name)} {{")
        for f in c.fields[:12]:
            lines.append(f"  {f.visibility} {f.name}{(': ' + f.type) if f.type else ''}")
        for m in c.methods[:14]:
            param_s = ", ".join(m.params)
            ret = f" : {m.returns}" if m.returns else ""
            lines.append(f"  {m.visibility} {m.name}({param_s}){ret}")
        lines.append("}")
    for c in shown:
        for p in c.parents:
            if p in shown_names:
                lines.append(f"{_sanitize(p)} <|-- {_sanitize(c.name)}")
    lines.append("@enduml")
    return "\n".join(lines)
