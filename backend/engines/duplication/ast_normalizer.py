"""
AST 节点归一化（语义级重复检测的核心）。

思路：
1. 将函数体的 AST 子树序列化为带"形状"的字符串，但去除标识符、字面量等会"改名抗检测"的细节
2. 同一形状的子树会得到相同的指纹，即使变量名/字面量完全不同
3. 这能识别出"换皮重复"——比如把循环变量 i 改成 idx、字符串内容修改而结构不变

适用范围：函数级粒度（更小粒度噪音过大），主要用于 Python（Java 由 token 路径补充）。
"""
from __future__ import annotations

import ast
import hashlib

from backend.engines.parser import ParsedFile
from backend.engines.parser.base import FunctionInfo


def _normalize_python_node(node: ast.AST) -> str:
    """递归把 Python AST 节点序列化为去除字面量/标识符的"骨架"字符串。"""
    if isinstance(node, ast.AST):
        parts = [type(node).__name__]
        for field, value in ast.iter_fields(node):
            if field in ("ctx", "type_comment"):
                continue
            if field == "id":  # ast.Name.id -> 标识符抹除
                parts.append("<ID>")
                continue
            if field in ("arg", "name", "attr", "asname", "module"):
                parts.append("<ID>")
                continue
            if field == "value" and isinstance(node, ast.Constant):
                if isinstance(value, str):
                    parts.append("<STR>")
                elif isinstance(value, (int, float, complex)):
                    parts.append("<NUM>")
                elif isinstance(value, bool):
                    parts.append("<BOOL>")
                elif value is None:
                    parts.append("<NONE>")
                else:
                    parts.append("<CONST>")
                continue
            if isinstance(value, list):
                parts.append("[" + ",".join(_normalize_python_node(v) for v in value) + "]")
            else:
                parts.append(_normalize_python_node(value))
        return "(" + " ".join(parts) + ")"
    if isinstance(node, str):
        return "<STR>"
    if isinstance(node, (int, float, complex)):
        return "<NUM>"
    return repr(node)


def fingerprint_function(func: FunctionInfo, language: str) -> str:
    """对函数生成 SHA-256 指纹。"""
    if func.raw_node is None:
        return ""
    if language == "python":
        skeleton = _normalize_python_node(func.raw_node)
    else:
        # Java 使用 javalang 节点的字符串表示作为兜底
        skeleton = type(func.raw_node).__name__ + ":" + str(getattr(func.raw_node, "name", ""))
        # 简单遍历子节点收集类型签名
        try:
            seq = []
            for path, node in func.raw_node:
                seq.append(type(node).__name__)
            skeleton += "::" + ",".join(seq)
        except Exception:
            pass
    return hashlib.sha256(skeleton.encode("utf-8")).hexdigest()


def fingerprint_all_functions(parsed: ParsedFile) -> dict[str, str]:
    """返回 {限定函数名: 指纹}。"""
    out: dict[str, str] = {}
    for f in parsed.functions:
        if f.end_line - f.start_line < 3:
            continue  # 过短函数跳过
        fp = fingerprint_function(f, parsed.language)
        if fp:
            out[f.qualified_name] = fp
    return out
