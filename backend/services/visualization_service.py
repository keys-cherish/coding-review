"""
可视化数据服务。

以 scan_id 为入口，从磁盘重新解析源码（只做必要部分），
结合数据库中的 issue/complexity/duplication 结果生成：
- dependency-graph
- call-graph
- sunburst (flame)
- treemap
- radar (6 dims)
- architecture pattern
- uml class diagram

为了提升响应速度：每个 scan 的 ParsedFile 列表会做一次进程内缓存。
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.engines.architecture import (
    build_call_graph,
    build_dependency_graph,
    compute_arch_radar,
    detect_cycles,
    extract_uml_classes,
    recognize_architecture,
    render_mermaid_class_diagram,
    render_plantuml_class_diagram,
)
from backend.engines.parser import ParsedFile, parse_file
from backend.models import ComplexityMetric, ScanTask, SourceFile, Version
from backend.utils import logger


_PARSE_CACHE: dict[int, list[ParsedFile]] = {}
_CACHE_LOCK = asyncio.Lock()


@dataclass
class ScanContext:
    scan: ScanTask
    version: Version
    upload_root: Path
    source_files: list[SourceFile] = field(default_factory=list)
    parsed_files: list[ParsedFile] = field(default_factory=list)
    complexity_by_file: dict[str, list[ComplexityMetric]] = field(default_factory=dict)



async def load_context(scan_id: int, db: AsyncSession) -> ScanContext:
    scan = await db.get(ScanTask, scan_id)
    if scan is None:
        raise LookupError(f"扫描任务 {scan_id} 不存在")
    version = await db.get(Version, scan.version_id)
    if version is None:
        raise LookupError(f"版本 {scan.version_id} 不存在")

    # 加载 SourceFile（按 version_id）
    sf_rows = (
        await db.execute(
            select(SourceFile).where(SourceFile.version_id == version.id)
        )
    ).scalars().all()

    # 去重（version 下同路径重复时留一个）
    uniq: dict[str, SourceFile] = {}
    for sf in sf_rows:
        uniq.setdefault(sf.relative_path, sf)
    source_files = list(uniq.values())

    # 加载 complexity（按 scan 对应的 source_file_id）
    cx_rows = (
        await db.execute(
            select(ComplexityMetric).where(
                ComplexityMetric.source_file_id.in_([sf.id for sf in source_files])
            )
        )
    ).scalars().all()
    cx_by_sfid: dict[int, list[ComplexityMetric]] = defaultdict(list)
    for c in cx_rows:
        cx_by_sfid[c.source_file_id].append(c)

    upload_root = Path(version.upload_path)

    ctx = ScanContext(
        scan=scan,
        version=version,
        upload_root=upload_root,
        source_files=source_files,
    )
    ctx.complexity_by_file = {
        sf.relative_path: cx_by_sfid.get(sf.id, []) for sf in source_files
    }
    return ctx


async def ensure_parsed(ctx: ScanContext) -> list[ParsedFile]:
    """按需解析源码文件并缓存。解析放到线程池避免阻塞事件循环。"""
    async with _CACHE_LOCK:
        cached = _PARSE_CACHE.get(ctx.scan.id)
        if cached is not None:
            ctx.parsed_files = cached
            return cached

    def _parse_all() -> list[ParsedFile]:
        out: list[ParsedFile] = []
        for sf in ctx.source_files:
            abs_path = ctx.upload_root / sf.relative_path
            if not abs_path.exists():
                continue
            try:
                pf = parse_file(abs_path, sf.language if sf.language != "unknown" else None)
                # 把 file_path 改成相对路径，所有下游的 module id 更干净
                pf.file_path = Path(sf.relative_path)
                out.append(pf)
            except Exception as e:
                logger.debug(f"解析 {abs_path} 跳过: {e}")
        return out

    parsed = await asyncio.to_thread(_parse_all)
    async with _CACHE_LOCK:
        _PARSE_CACHE[ctx.scan.id] = parsed
    ctx.parsed_files = parsed
    return parsed


def invalidate_cache(scan_id: int | None = None) -> None:
    if scan_id is None:
        _PARSE_CACHE.clear()
    else:
        _PARSE_CACHE.pop(scan_id, None)


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------


def _category_of(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if parts else "root"


def build_dependency_graph_payload(parsed_files: list[ParsedFile]) -> dict:
    graph = build_dependency_graph(parsed_files)
    cycles = detect_cycles(graph)

    categories: list[str] = []
    cat_index: dict[str, int] = {}
    for node in graph.nodes.values():
        cat = _category_of(node.file_path)
        if cat not in cat_index:
            cat_index[cat] = len(categories)
            categories.append(cat)

    cycle_node_ids: set[str] = set()
    for c in cycles:
        cycle_node_ids.update(c.modules)

    nodes_payload = []
    for mid, node in graph.nodes.items():
        cat = _category_of(node.file_path)
        nodes_payload.append({
            "id": mid,
            "name": PurePosixPath(node.file_path).name or mid,
            "file_path": node.file_path,
            "category": cat_index[cat],
            "category_name": cat,
            "size": max(8, min(60, node.loc / 10 + 12)),
            "loc": node.loc,
            "fan_in": node.fan_in,
            "fan_out": node.fan_out,
            "in_cycle": mid in cycle_node_ids,
        })

    links_payload = []
    for (src, dst), edge in graph.edges.items():
        links_payload.append({
            "source": src,
            "target": dst,
            "value": edge.count,
        })

    cycles_payload = [
        {
            "modules": c.modules,
            "shortest_cycle": c.shortest_cycle,
            "size": c.size,
            "severity": c.severity,
            "description": c.description,
        }
        for c in cycles
    ]

    return {
        "nodes": nodes_payload,
        "links": links_payload,
        "categories": [{"name": c} for c in categories],
        "cycles": cycles_payload,
        "stats": graph.stats(),
    }


# ---------------------------------------------------------------------------
# Call graph
# ---------------------------------------------------------------------------


def build_call_graph_payload(
    parsed_files: list[ParsedFile],
    complexity_by_file: dict[str, list[ComplexityMetric]],
) -> dict:
    cg = build_call_graph(parsed_files, complexity_by_file)
    out = cg.to_dict()
    # 节点 category 用文件顶层目录，供前端分色
    for n in out["nodes"]:
        n["category_name"] = _category_of(n["file"])
    return out


# ---------------------------------------------------------------------------
# Sunburst / Treemap
# ---------------------------------------------------------------------------


def _insert_hierarchy(root: dict, path_parts: list[str], leaf_value: int, leaf_meta: dict) -> None:
    cur = root
    for i, part in enumerate(path_parts):
        children = cur.setdefault("children", [])
        existing = next((c for c in children if c["name"] == part), None)
        if existing is None:
            existing = {"name": part, "children": []}
            children.append(existing)
        cur = existing
    cur["value"] = leaf_value
    cur.update(leaf_meta)


def _sum_values(node: dict) -> int:
    if "children" in node and node["children"]:
        total = 0
        for c in node["children"]:
            total += _sum_values(c)
        node["value"] = total
        return total
    return int(node.get("value", 0) or 0)


def build_sunburst_payload(
    parsed_files: list[ParsedFile],
    complexity_by_file: dict[str, list[ComplexityMetric]],
) -> dict:
    """目录 → 文件 → 函数。value 用 LOC。"""
    root: dict = {"name": "项目", "children": []}
    for pf in parsed_files:
        rel = PurePosixPath(str(pf.file_path)).as_posix()
        parts = list(PurePosixPath(rel).parts)
        loc = pf.total_lines or 1
        if pf.functions:
            file_node_path = parts
            for fn in pf.functions[:60]:
                fn_loc = max(1, fn.end_line - fn.start_line + 1)
                _insert_hierarchy(root, file_node_path + [fn.name], fn_loc, {})
        else:
            _insert_hierarchy(root, parts, loc, {})
    _sum_values(root)
    return root


def build_treemap_payload(
    parsed_files: list[ParsedFile],
    complexity_by_file: dict[str, list[ComplexityMetric]],
    issues_per_file: dict[str, int],
) -> dict:
    """目录 → 文件 → 函数，value=LOC，colorValue=平均复杂度或问题数。"""
    root: dict = {"name": "项目", "children": []}

    for pf in parsed_files:
        rel = PurePosixPath(str(pf.file_path)).as_posix()
        parts = list(PurePosixPath(rel).parts)
        cx_list = complexity_by_file.get(rel, [])
        file_issues = issues_per_file.get(rel, 0)

        if pf.functions:
            for fn in pf.functions[:60]:
                cx = next((c for c in cx_list if c.function_name == fn.name), None)
                fn_loc = max(1, fn.end_line - fn.start_line + 1)
                color = int(getattr(cx, "cyclomatic", 1)) if cx else 1
                _insert_hierarchy(root, parts + [fn.name], fn_loc, {
                    "colorValue": color,
                    "cyclomatic": color,
                })
        else:
            _insert_hierarchy(root, parts, pf.total_lines or 1, {
                "colorValue": file_issues,
            })

    _sum_values(root)
    return root


# ---------------------------------------------------------------------------
# Previous scan for radar comparison
# ---------------------------------------------------------------------------


async def find_previous_scan(db: AsyncSession, scan: ScanTask) -> ScanTask | None:
    version = await db.get(Version, scan.version_id)
    if version is None:
        return None
    # 找同 project 的上一个 completed scan（不是自己）
    stmt = (
        select(ScanTask)
        .join(Version, Version.id == ScanTask.version_id)
        .where(
            Version.project_id == version.project_id,
            ScanTask.id != scan.id,
            ScanTask.status == "done",
            ScanTask.created_at <= scan.created_at,
        )
        .order_by(desc(ScanTask.created_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalars().first()
