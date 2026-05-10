"""
架构模式识别。

基于目录名指纹 + 依赖方向特征，识别常见架构模式：
MVC / MVP / MVVM / 三层 / DDD / Clean / Hexagonal / CQRS / 微服务 /
Go 标准布局 / 事件驱动 / 单体。

输出带置信度（0~1）的候选列表，外加 primary 首选与层级结构。
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from backend.engines.architecture.dependency_graph import DependencyGraph


@dataclass
class ArchPattern:
    """识别出的一个架构模式候选。"""
    pattern: str
    confidence: float
    reason: str
    evidence: list[str] = field(default_factory=list)


# 典型目录关键词 → 层语义
_LAYER_KEYWORDS: dict[str, list[str]] = {
    "controller": ["controller", "controllers", "handler", "handlers", "api", "rest", "web", "routes", "router", "routers", "views"],
    "service":    ["service", "services", "biz", "business", "usecase", "usecases", "application", "logic"],
    "repository": ["repository", "repositories", "repo", "dao", "mapper", "mappers", "persistence"],
    "domain":     ["domain", "model", "models", "entity", "entities", "aggregate", "aggregates"],
    "infra":      ["infra", "infrastructure", "adapter", "adapters", "gateway", "gateways"],
    "cmd":        ["cmd", "main"],
    "internal":   ["internal", "pkg"],
    "view":       ["view", "views", "ui", "frontend", "template", "templates"],
    "viewmodel":  ["viewmodel", "viewmodels", "presenter", "presenters"],
    "event":      ["event", "events", "message", "messages", "queue", "broker", "kafka", "mq"],
    "command":    ["command", "commands"],
    "query":      ["query", "queries"],
}


def _classify_dir(segment: str) -> list[str]:
    """一个目录名可以命中多个语义（评分式）。"""
    low = segment.lower()
    tags = []
    for tag, keys in _LAYER_KEYWORDS.items():
        if low in keys:
            tags.append(tag)
    return tags


def _collect_layer_evidence(graph: DependencyGraph) -> tuple[dict[str, list[str]], dict[str, list[str]], list[str]]:
    """返回 layer→files 映射 + dir→files + 所有顶层目录。"""
    layer_files: dict[str, list[str]] = defaultdict(list)
    dir_files: dict[str, list[str]] = defaultdict(list)
    top_dirs: set[str] = set()

    for mid, node in graph.nodes.items():
        segments = PurePosixPath(node.file_path).parts
        if not segments:
            continue
        top_dirs.add(segments[0])
        for seg in segments[:-1]:
            dir_files[seg].append(node.file_path)
            for tag in _classify_dir(seg):
                layer_files[tag].append(node.file_path)
    return layer_files, dir_files, sorted(top_dirs)


def _layer_score(layer_files: dict[str, list[str]], required: list[str]) -> tuple[float, list[str]]:
    """根据命中层数量按比例打分。"""
    hit = [r for r in required if layer_files.get(r)]
    return (len(hit) / len(required), hit)


def _microservice_signal(top_dirs: list[str], dir_files: dict[str, list[str]]) -> float:
    """top-level 存在多个 service 风格目录，且每个都带 cmd/main 入口 → 微服务。"""
    service_like = [d for d in top_dirs if re.search(r"(service|svc|gateway|worker)", d, re.I)]
    if len(service_like) >= 2:
        return min(1.0, 0.4 + 0.1 * len(service_like))
    return 0.0


def _event_driven_signal(layer_files: dict[str, list[str]]) -> float:
    if layer_files.get("event"):
        return min(1.0, 0.3 + 0.1 * min(7, len(layer_files["event"])))
    return 0.0


def _go_stdlayout_signal(top_dirs: list[str]) -> float:
    markers = sum(1 for d in top_dirs if d in ("cmd", "internal", "pkg", "api"))
    if markers >= 2:
        return min(1.0, 0.4 + 0.2 * markers)
    return 0.0


def _cross_layer_ratio(graph: DependencyGraph, layer_files: dict[str, list[str]]) -> float:
    """跨层调用占比：越高说明分层越混乱；返回 0~1。"""
    file_to_layer: dict[str, str] = {}
    for layer, files in layer_files.items():
        for f in files:
            file_to_layer.setdefault(f, layer)

    total = len(graph.edges) or 1
    cross = 0
    for (src_id, dst_id), _ in graph.edges.items():
        src_file = graph.nodes[src_id].file_path if src_id in graph.nodes else ""
        dst_file = graph.nodes[dst_id].file_path if dst_id in graph.nodes else ""
        sl = file_to_layer.get(src_file)
        dl = file_to_layer.get(dst_file)
        if sl and dl and sl != dl:
            cross += 1
    return cross / total


def recognize_architecture(graph: DependencyGraph) -> dict:
    """执行架构识别，返回 {detected, primary, layers}。"""
    layer_files, dir_files, top_dirs = _collect_layer_evidence(graph)

    candidates: list[ArchPattern] = []

    # 三层 / MVC
    three_tier_score, three_hit = _layer_score(layer_files, ["controller", "service", "repository"])
    if three_tier_score > 0:
        candidates.append(ArchPattern(
            pattern="三层架构 (Controller / Service / Repository)",
            confidence=three_tier_score * 0.9,
            reason=f"命中层: {', '.join(three_hit)}",
            evidence=[layer_files[l][0] for l in three_hit if layer_files[l]][:5],
        ))

    mvc_score, mvc_hit = _layer_score(layer_files, ["controller", "service", "view"])
    if mvc_score >= 0.66:
        candidates.append(ArchPattern(
            pattern="MVC",
            confidence=mvc_score * 0.85,
            reason="同时发现 Controller 与 View 目录",
            evidence=[layer_files[l][0] for l in mvc_hit if layer_files[l]][:5],
        ))

    mvvm_score, _ = _layer_score(layer_files, ["view", "viewmodel"])
    if mvvm_score >= 1.0:
        candidates.append(ArchPattern(
            pattern="MVVM",
            confidence=0.8,
            reason="同时发现 View 与 ViewModel",
            evidence=[layer_files["viewmodel"][0]] if layer_files.get("viewmodel") else [],
        ))

    # DDD
    ddd_score, ddd_hit = _layer_score(layer_files, ["domain", "repository", "service"])
    if ddd_score >= 0.66:
        candidates.append(ArchPattern(
            pattern="DDD (领域驱动设计)",
            confidence=ddd_score * 0.85,
            reason=f"命中领域层: {', '.join(ddd_hit)}",
            evidence=[layer_files[l][0] for l in ddd_hit if layer_files[l]][:5],
        ))

    # Clean / Hexagonal：同时存在 infra/adapter + domain
    if layer_files.get("infra") and layer_files.get("domain"):
        candidates.append(ArchPattern(
            pattern="Clean / Hexagonal",
            confidence=0.75,
            reason="发现基础设施(adapter/infra)与领域(domain)双向隔离",
            evidence=[layer_files["infra"][0], layer_files["domain"][0]],
        ))

    # CQRS
    if layer_files.get("command") and layer_files.get("query"):
        candidates.append(ArchPattern(
            pattern="CQRS",
            confidence=0.85,
            reason="命令与查询目录分离",
            evidence=[layer_files["command"][0], layer_files["query"][0]],
        ))

    # Event-driven
    e_score = _event_driven_signal(layer_files)
    if e_score > 0:
        candidates.append(ArchPattern(
            pattern="事件驱动",
            confidence=e_score,
            reason="出现 event/message/queue 目录",
            evidence=layer_files["event"][:3],
        ))

    # Go 标准布局
    go_score = _go_stdlayout_signal(top_dirs)
    if go_score > 0:
        candidates.append(ArchPattern(
            pattern="Go 标准项目布局",
            confidence=go_score,
            reason="顶层出现 cmd/internal/pkg 标记",
            evidence=[d for d in top_dirs if d in ("cmd", "internal", "pkg", "api")][:4],
        ))

    # 微服务
    ms_score = _microservice_signal(top_dirs, dir_files)
    if ms_score > 0:
        candidates.append(ArchPattern(
            pattern="微服务 (Microservices)",
            confidence=ms_score,
            reason="顶层存在多个独立 service / gateway 模块",
            evidence=[d for d in top_dirs if re.search(r"(service|svc|gateway|worker)", d, re.I)][:5],
        ))

    # 单体兜底：没有明显层次特征 & 只有一个顶层目录
    if not candidates and len(top_dirs) <= 2 and len(graph.nodes) > 0:
        candidates.append(ArchPattern(
            pattern="单体 (Monolith)",
            confidence=0.5,
            reason="未识别到明显分层，项目结构扁平",
            evidence=top_dirs[:3],
        ))

    candidates.sort(key=lambda p: p.confidence, reverse=True)
    primary = candidates[0].pattern if candidates else "未识别"

    layers_out = []
    for layer in ("controller", "service", "repository", "domain", "infra", "view", "viewmodel", "event", "command", "query"):
        files = layer_files.get(layer, [])
        if not files:
            continue
        # 取命中该 layer 的目录 set
        dirs = sorted({str(PurePosixPath(f).parts[-2]) for f in files if len(PurePosixPath(f).parts) >= 2})
        layers_out.append({
            "name": layer,
            "dirs": dirs,
            "files_count": len(files),
        })

    return {
        "detected": [
            {
                "pattern": c.pattern,
                "confidence": round(c.confidence, 3),
                "reason": c.reason,
                "evidence": c.evidence,
            }
            for c in candidates
        ],
        "primary": primary,
        "layers": layers_out,
        "top_dirs": top_dirs,
        "cross_layer_ratio": round(_cross_layer_ratio(graph, layer_files), 3),
    }
