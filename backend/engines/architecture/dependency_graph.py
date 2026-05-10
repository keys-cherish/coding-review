"""
依赖图构建器。

设计目标
--------
在不依赖本地构建环境的前提下，基于 Tree-sitter 抽取的 ImportInfo 与
FunctionInfo/ClassInfo，快速构建跨文件的依赖有向图。

输出结构
--------
DependencyGraph：
- nodes: 模块节点集合（模块 ≈ 源文件的规范化相对路径）
- edges: 模块 → 模块 的导入依赖（可含多条、带边权）
- symbol_table: 模块 → {类, 函数, 接口} 的符号索引

这张图是上层所有架构分析的基础（循环依赖、分层违规、上帝类拓扑等都依赖它）。

性能
----
- 全内存 dict/set，10 万行代码级别毫秒完成
- 使用 Map-Reduce 模式：先并发抽取 per-file 元数据，再串行聚合
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Iterable

from backend.engines.parser.base import ParsedFile


@dataclass
class DependencyEdge:
    """模块间的一条依赖边。"""
    src: str              # 源模块（规范化路径，如 'backend/services/upload'）
    dst: str              # 目标模块
    raw_imports: list[str] = field(default_factory=list)  # 原始 import 字符串
    count: int = 1        # 同源→同目标的多次 import 合并后的计数
    is_wildcard: bool = False


@dataclass
class ModuleNode:
    """模块节点（粒度：一个源文件 ≈ 一个模块）。"""
    module_id: str                       # 规范化标识（不含扩展名）
    file_path: str                       # 相对路径
    language: str
    loc: int = 0
    class_names: list[str] = field(default_factory=list)
    function_names: list[str] = field(default_factory=list)
    interface_names: list[str] = field(default_factory=list)
    # 拓扑统计（在图构建完后回填）
    fan_in: int = 0                      # 被多少个模块依赖
    fan_out: int = 0                     # 依赖多少个模块
    layer: str = ""                      # 分层推断结果（controller/service/...）


@dataclass
class DependencyGraph:
    """依赖图。

    为了便于图算法（Tarjan/DFS 等）：同时维护 nodes、adjacency、reverse_adj。
    """
    nodes: dict[str, ModuleNode] = field(default_factory=dict)
    edges: dict[tuple[str, str], DependencyEdge] = field(default_factory=dict)
    adjacency: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse_adj: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    # 额外索引：类名 → 所在模块（用于 import 名称 → 模块 的反查）
    symbol_index: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    # ---- 只读便捷方法 ----

    def successors(self, module: str) -> set[str]:
        return self.adjacency.get(module, set())

    def predecessors(self, module: str) -> set[str]:
        return self.reverse_adj.get(module, set())

    def stats(self) -> dict:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "avg_fan_out": round(
                sum(n.fan_out for n in self.nodes.values()) / max(1, len(self.nodes)),
                2,
            ),
            "max_fan_in": max((n.fan_in for n in self.nodes.values()), default=0),
        }


# ---------------------------------------------------------------------------
# 构建器
# ---------------------------------------------------------------------------

# 语言 → 常见源码根前缀（用于剥离得到模块标识）
_SRC_ROOT_HINTS = (
    "src/main/java/",
    "src/main/kotlin/",
    "src/",
    "app/",
    "internal/",
    "pkg/",
    "lib/",
)

# 将 import 字符串标准化为"点分路径片段列表"的正则
_DOT_SPLIT = re.compile(r"[./\\]+")


def _relative_path(pf: ParsedFile) -> str:
    """从 ParsedFile 提取相对路径（尽可能短且可读）。"""
    # ParsedFile.file_path 是 Path；工程内一般已是相对路径
    p = getattr(pf, "file_path", "")
    if hasattr(p, "as_posix"):
        return p.as_posix()
    return str(p).replace("\\", "/")


def _normalize_module_id(relative_path: str) -> str:
    """把源文件路径转换为统一的模块标识。

    规则：
    - 使用 POSIX 分隔符
    - 剥离常见源码根前缀（如 src/main/java）
    - 去掉扩展名
    - __init__.py 合并为所在包
    """
    p = PurePosixPath(relative_path.replace("\\", "/"))
    as_str = str(p)

    for hint in _SRC_ROOT_HINTS:
        if as_str.startswith(hint):
            as_str = as_str[len(hint):]
            break

    # 去扩展名
    if "." in p.name:
        as_str = as_str.rsplit(".", 1)[0]

    # __init__ 合并到上一级
    if as_str.endswith("/__init__"):
        as_str = as_str[: -len("/__init__")]

    return as_str or p.stem


def _tokenize_import(raw: str) -> list[str]:
    """从 raw import 语句中提取候选模块 token（多段）。

    示例：
      'import java.util.List;'      → ['java','util','List']
      'from backend.models import X' → ['backend','models','X']
      'require("./utils/helper")'    → ['utils','helper']
    """
    # 去掉常见前缀关键字
    cleaned = re.sub(
        r"^\s*(import|from|package|require|using|include|use)\s+",
        "",
        raw.strip(),
        flags=re.IGNORECASE,
    )
    # 去引号、分号、括号
    cleaned = re.sub(r"['\";()`]", "", cleaned)
    # 去尾部 'as X'
    cleaned = re.sub(r"\s+as\s+\w+", "", cleaned, flags=re.IGNORECASE)
    # 首个空白前的部分视为模块路径，例如 'a.b.c import X' → 'a.b.c'
    # 但对于 'from a.b import X' 需要保留 X
    # 这里拆两段最稳
    parts = re.split(r"\s+import\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        path, names = parts
        tokens = [t for t in _DOT_SPLIT.split(path) if t]
        # names 里可能是 "A, B, C"
        for n in re.split(r"[,\s]+", names):
            if n and n != "*":
                tokens.append(n)
        return tokens
    return [t for t in _DOT_SPLIT.split(cleaned) if t]


def _best_match(candidates: Iterable[str], module_ids: set[str], symbol_index: dict[str, set[str]]) -> str | None:
    """给定 import 的 token 序列，尝试匹配已知模块 id。

    匹配优先级：
    1) 拼接后缀完全等于某个 module_id
    2) 符号索引命中（类名/函数名）
    3) 模块 id 以该 token 结尾
    """
    tokens = [t for t in candidates if t]
    if not tokens:
        return None

    # 1) 拼接做后缀匹配
    joined = "/".join(tokens)
    for mid in module_ids:
        if mid.endswith(joined) or joined.endswith(mid):
            return mid

    # 2) 符号表命中最后一个 token（最可能是类/函数名）
    last = tokens[-1]
    hits = symbol_index.get(last)
    if hits:
        # 如果有多处同名，取最短路径（通常是顶层定义）
        return min(hits, key=len)

    # 3) 单 token 前缀匹配
    for mid in module_ids:
        segs = mid.split("/")
        if segs and segs[-1] == last:
            return mid

    return None


def build_dependency_graph(parsed_files: list[ParsedFile]) -> DependencyGraph:
    """从解析结果批量构建依赖图。

    Args:
        parsed_files: Tree-sitter 已解析好的文件元数据列表。

    Returns:
        DependencyGraph：完整的模块依赖视图。
    """
    graph = DependencyGraph()

    # ---- Pass 1：建节点 + 符号索引 ----
    for pf in parsed_files:
        rel = _relative_path(pf)
        mid = _normalize_module_id(rel)
        node = ModuleNode(
            module_id=mid,
            file_path=rel,
            language=pf.language,
            loc=pf.total_lines,
        )

        for cls in pf.classes:
            node.class_names.append(cls.name)
            graph.symbol_index[cls.name].add(mid)
            # 启发式：名字含 Interface/接口 归入 interface
            if "Interface" in cls.name or (cls.name.startswith("I") and len(cls.name) > 1 and cls.name[1:2].isupper()):
                node.interface_names.append(cls.name)
        for fn in pf.functions:
            node.function_names.append(fn.name)
            graph.symbol_index[fn.name].add(mid)

        graph.nodes[mid] = node

    module_ids = set(graph.nodes.keys())

    # ---- Pass 2：连边 ----
    for pf in parsed_files:
        src = _normalize_module_id(_relative_path(pf))

        for imp in pf.imports:
            raw = imp.module if hasattr(imp, "module") else str(imp)
            tokens = _tokenize_import(raw)
            dst = _best_match(tokens, module_ids, graph.symbol_index)
            if dst is None or dst == src:
                continue

            key = (src, dst)
            if key in graph.edges:
                edge = graph.edges[key]
                edge.count += 1
                edge.raw_imports.append(raw)
            else:
                edge = DependencyEdge(
                    src=src,
                    dst=dst,
                    raw_imports=[raw],
                    is_wildcard=getattr(imp, "is_wildcard", False) or "*" in raw,
                )
                graph.edges[key] = edge
                graph.adjacency[src].add(dst)
                graph.reverse_adj[dst].add(src)

    # ---- Pass 3：回填 fan_in / fan_out ----
    for mid, node in graph.nodes.items():
        node.fan_out = len(graph.adjacency.get(mid, set()))
        node.fan_in = len(graph.reverse_adj.get(mid, set()))

    return graph
