"""
函数调用图构建器。

策略（不追求 100% 精确）：
- 对每个文件，扫描 AST 层的函数调用表达式（Python: ast.Call；Java: MethodInvocation）
- 调用名称匹配范围：同文件内定义的函数 + 同模块通过 import 引入的名字
- 节点复杂度：来自 complexity 引擎或 LOC 估算

输出结构：
    nodes: [{id, name, file, complexity}]
    links: [{source, target}]
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from backend.engines.parser.base import ParsedFile


@dataclass
class CallNode:
    id: str
    name: str
    file: str
    complexity: int = 1


@dataclass
class CallGraph:
    nodes: dict[str, CallNode] = field(default_factory=dict)
    links: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {"id": n.id, "name": n.name, "file": n.file, "complexity": n.complexity}
                for n in self.nodes.values()
            ],
            "links": [{"source": s, "target": t} for s, t in self.links],
        }


def _py_calls_in(func_node: ast.AST) -> list[str]:
    """收集一个 Python 函数体内的被调用标识名（ast.Call.func.id / attribute）。"""
    names: list[str] = []
    for n in ast.walk(func_node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                names.append(f.id)
            elif isinstance(f, ast.Attribute):
                names.append(f.attr)
    return names


def _complexity_map(complexities: list) -> dict[str, int]:
    """func qualified_name or name → cyclomatic."""
    m: dict[str, int] = {}
    for c in complexities or []:
        name = getattr(c, "qualified_name", None) or getattr(c, "function_name", "")
        m[name] = int(getattr(c, "cyclomatic", 1) or 1)
        # 同时登记 short name
        if "." in name:
            m.setdefault(name.rsplit(".", 1)[-1], int(getattr(c, "cyclomatic", 1) or 1))
    return m


def build_call_graph(
    parsed_files: list[ParsedFile],
    complexities_by_file: dict[str, list] | None = None,
) -> CallGraph:
    """构建调用图。

    Args:
        parsed_files: 已解析的文件列表
        complexities_by_file: {file_path_posix: [FunctionComplexity, ...]} 可选
    """
    cg = CallGraph()
    complexities_by_file = complexities_by_file or {}

    # Step 1: 登记所有函数节点 + 构建 per-file 符号表
    file_funcs: dict[str, dict[str, str]] = {}  # file -> {short_name: node_id}
    all_names: dict[str, list[str]] = {}        # short_name -> [node_id,...]

    for pf in parsed_files:
        rel = PurePosixPath(str(pf.file_path)).as_posix()
        cx_map = _complexity_map(complexities_by_file.get(rel, []))
        fmap: dict[str, str] = {}
        for fn in pf.functions:
            node_id = f"{rel}::{fn.qualified_name or fn.name}"
            complexity = cx_map.get(fn.qualified_name or "", cx_map.get(fn.name, 1))
            cg.nodes[node_id] = CallNode(
                id=node_id,
                name=fn.name,
                file=rel,
                complexity=complexity,
            )
            fmap[fn.name] = node_id
            all_names.setdefault(fn.name, []).append(node_id)
        file_funcs[rel] = fmap

    # Step 2: 对每个函数抽 calls 并连边
    for pf in parsed_files:
        rel = PurePosixPath(str(pf.file_path)).as_posix()
        fmap = file_funcs.get(rel, {})
        if pf.language != "python":
            continue  # 非 Python 只做节点，不连边（保持健壮）
        for fn in pf.functions:
            if not getattr(fn, "raw_node", None):
                continue
            src_id = f"{rel}::{fn.qualified_name or fn.name}"
            calls = _py_calls_in(fn.raw_node)
            seen: set[str] = set()
            for called in calls:
                target_id: str | None = None
                if called in fmap:
                    target_id = fmap[called]
                else:
                    # 在全局同名候选里挑，如果项目里只有一个同名函数，则连过去
                    cands = all_names.get(called, [])
                    if len(cands) == 1:
                        target_id = cands[0]
                if target_id and target_id != src_id and target_id not in seen:
                    cg.links.append((src_id, target_id))
                    seen.add(target_id)

    return cg
