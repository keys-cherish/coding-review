"""
循环依赖检测。

使用 Tarjan 强连通分量（SCC）算法：
- 时间复杂度 O(V+E)
- 所有节点数大于 1 的 SCC 即为一个"相互循环"的模块组
- 节点数等于 1 但存在自环的节点同样算作"自循环"

返回的 CycleInfo 提供：
- 循环涉及的模块列表
- 最短循环路径（用于报错时的展示）
- 严重度估算（环规模 + 涉及分层跨度）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from backend.engines.architecture.dependency_graph import DependencyGraph


@dataclass
class CycleInfo:
    """一条循环依赖。"""
    modules: list[str]                    # 属于该 SCC 的模块
    shortest_cycle: list[str] = field(default_factory=list)  # 展示用最短环
    size: int = 0
    severity: str = "medium"              # low/medium/high/critical
    description: str = ""


def _tarjan_scc(graph: DependencyGraph) -> list[list[str]]:
    """标准 Tarjan 算法求强连通分量。

    使用迭代栈而非递归，避免 Python 的递归深度限制
    （大型项目依赖链可能超过 1000 层）。
    """
    index_counter = [0]
    stack: list[str] = []
    lowlinks: dict[str, int] = {}
    index: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    result: list[list[str]] = []

    def strongconnect(start: str) -> None:
        # 用显式栈模拟递归
        work_stack: list[tuple[str, Iterable[str]]] = [(start, iter(sorted(graph.successors(start))))]
        index[start] = index_counter[0]
        lowlinks[start] = index_counter[0]
        index_counter[0] += 1
        stack.append(start)
        on_stack[start] = True

        while work_stack:
            node, it = work_stack[-1]
            advanced = False
            for neighbor in it:
                if neighbor not in index:
                    index[neighbor] = index_counter[0]
                    lowlinks[neighbor] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(neighbor)
                    on_stack[neighbor] = True
                    work_stack.append((neighbor, iter(sorted(graph.successors(neighbor)))))
                    advanced = True
                    break
                elif on_stack.get(neighbor):
                    lowlinks[node] = min(lowlinks[node], index[neighbor])
            if not advanced:
                work_stack.pop()
                if lowlinks[node] == index[node]:
                    component: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        component.append(w)
                        if w == node:
                            break
                    if len(component) > 1 or (len(component) == 1 and component[0] in graph.successors(component[0])):
                        result.append(component)
                if work_stack:
                    parent, _ = work_stack[-1]
                    lowlinks[parent] = min(lowlinks[parent], lowlinks[node])

    for v in list(graph.nodes.keys()):
        if v not in index:
            strongconnect(v)

    return result


def _find_shortest_cycle(graph: DependencyGraph, scc_nodes: list[str]) -> list[str]:
    """在一个 SCC 内部，取某节点出发找到的最短回路，用于展示。"""
    if len(scc_nodes) == 1:
        node = scc_nodes[0]
        if node in graph.successors(node):
            return [node, node]
        return scc_nodes

    # BFS 找最短环
    start = scc_nodes[0]
    allowed = set(scc_nodes)
    # 从 start 出发回到 start
    parents: dict[str, str] = {}
    visited = {start}
    queue: list[str] = [start]
    target = None
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        for nxt in graph.successors(cur):
            if nxt not in allowed:
                continue
            if nxt == start and cur != start:
                parents[nxt] = cur
                target = nxt
                break
            if nxt not in visited:
                visited.add(nxt)
                parents[nxt] = cur
                queue.append(nxt)
        if target is not None:
            break

    if target is None:
        return scc_nodes  # 兜底

    # 回溯路径
    path = [start]
    cur = parents.get(start)
    guard = 0
    while cur is not None and cur != start and guard < 1024:
        path.append(cur)
        cur = parents.get(cur)
        guard += 1
    path.append(start)
    path.reverse()
    return path


def _severity_of(size: int, is_self_loop: bool) -> str:
    if is_self_loop:
        return "low"
    if size >= 8:
        return "critical"
    if size >= 5:
        return "high"
    if size >= 3:
        return "medium"
    return "low"


def detect_cycles(graph: DependencyGraph) -> list[CycleInfo]:
    """检测所有循环依赖，按严重度降序返回。"""
    sccs = _tarjan_scc(graph)
    cycles: list[CycleInfo] = []
    for comp in sccs:
        size = len(comp)
        is_self = size == 1
        shortest = _find_shortest_cycle(graph, comp)
        severity = _severity_of(size, is_self)
        if is_self:
            desc = f"模块 {comp[0]} 自引用"
        else:
            desc = f"{size} 个模块形成循环依赖：" + " → ".join(shortest)
        cycles.append(CycleInfo(
            modules=sorted(comp),
            shortest_cycle=shortest,
            size=size,
            severity=severity,
            description=desc,
        ))

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    cycles.sort(key=lambda c: (order[c.severity], -c.size))
    return cycles
