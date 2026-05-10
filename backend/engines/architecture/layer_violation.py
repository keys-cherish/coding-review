"""
分层违规检测。

思路
----
1. 复用 `pattern_recognizer._collect_layer_evidence` 把文件分到 layer
2. 为经典层次模式定义允许的调用方向：
     controller → service → repository → domain
     controller → service → infra (允许跨到 infra/共享)
     view → viewmodel → domain
     command / query → domain
3. 遍历依赖图边 (src_file → dst_file)，若两端都映射到不同 layer
   且方向违反约定，则记为违规

对外函数
--------
- detect_layer_violations(graph) -> {violations: [...], summary: {...}}
- violation 条目包含：src_file, src_layer, dst_file, dst_layer, reason, severity
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.engines.architecture.dependency_graph import DependencyGraph
from backend.engines.architecture.pattern_recognizer import _collect_layer_evidence


# 层级数字：数字越大越"下层"，被依赖；数字越小越"上层"，主动调用
# 允许从小 → 大（上层依赖下层），禁止大 → 小（下层反过来依赖上层）
# 同层允许；未分层 / 公共层不参与检测
LAYER_ORDER: dict[str, int] = {
    # 经典 MVC / 三层
    "controller": 10,
    "service":    20,
    "repository": 30,
    "domain":     40,
    "infra":      50,
    # MVVM
    "view":       10,
    "viewmodel":  20,
    # CQRS
    "command":    20,
    "query":      20,
    # event 层可被上层触发，也可监听上层事件 — 不参与严格方向约束
}

# 同义名归一（以便支持不同命名风格的项目）
LAYER_ALIAS: dict[str, str] = {
    "ctrl": "controller",
    "handler": "controller",
    "api": "controller",
    "rest": "controller",
    "web": "controller",
    "services": "service",
    "svc": "service",
    "usecase": "service",
    "biz": "service",
    "dao": "repository",
    "repo": "repository",
    "mapper": "repository",
    "repositories": "repository",
    "model": "domain",
    "entity": "domain",
    "entities": "domain",
    "domains": "domain",
    "infrastructure": "infra",
    "persistence": "infra",
    "views": "view",
    "pages": "view",
    "vm": "viewmodel",
    "commands": "command",
    "queries": "query",
}


@dataclass
class LayerViolation:
    src_file: str
    src_layer: str
    dst_file: str
    dst_layer: str
    reason: str
    severity: str  # error / warning


def _canonical(layer: str) -> str:
    layer = layer.lower()
    return LAYER_ALIAS.get(layer, layer)


def _build_file_to_layer(graph: DependencyGraph) -> dict[str, str]:
    layer_files, _, _ = _collect_layer_evidence(graph)
    file_to_layer: dict[str, str] = {}
    for layer, files in layer_files.items():
        canon = _canonical(layer)
        if canon not in LAYER_ORDER:
            continue
        for f in files:
            file_to_layer.setdefault(f, canon)
    return file_to_layer


def _classify(src_layer: str, dst_layer: str) -> tuple[bool, str, str]:
    """返回 (is_violation, reason, severity)。"""
    if src_layer == dst_layer:
        return False, "", ""
    s = LAYER_ORDER.get(src_layer)
    d = LAYER_ORDER.get(dst_layer)
    if s is None or d is None:
        return False, "", ""
    # 上层依赖下层：合法
    if s < d:
        return False, "", ""
    # 下层反向依赖上层：违规
    if s > d:
        reason = f"{src_layer} 依赖了更上层的 {dst_layer}，违反单向依赖约束"
        # controller 直接入到 repository/infra：跳过 service
        severity = "error" if src_layer in ("repository", "domain", "infra") else "warning"
        return True, reason, severity
    return False, "", ""


def _extra_skip_layer_check(src_layer: str, dst_layer: str) -> tuple[bool, str, str]:
    """额外规则：controller 不应直接调用 repository（应经过 service）。"""
    if src_layer == "controller" and dst_layer in ("repository", "infra"):
        return True, f"{src_layer} 直接调用 {dst_layer}，跳过了 service 层", "warning"
    if src_layer == "view" and dst_layer in ("repository", "infra", "domain"):
        return True, f"{src_layer} 直接访问 {dst_layer}，应经过 viewmodel", "warning"
    return False, "", ""


def detect_layer_violations(graph: DependencyGraph) -> dict:
    """扫描依赖边，输出违规清单。

    返回
    ----
    {
      "violations": [LayerViolation.__dict__, ...],
      "summary": {
          "total_edges": int,
          "classified_edges": int,   # 两端都被映射到某层的边
          "violation_count": int,
          "violation_ratio": float,  # violation / classified
          "by_severity": {"error": n, "warning": n},
          "layers_present": [..]
      }
    }
    """
    file_to_layer = _build_file_to_layer(graph)
    violations: list[LayerViolation] = []
    classified = 0

    for (src_id, dst_id), _edge in graph.edges.items():
        src_file = graph.nodes[src_id].file_path if src_id in graph.nodes else ""
        dst_file = graph.nodes[dst_id].file_path if dst_id in graph.nodes else ""
        sl = file_to_layer.get(src_file)
        dl = file_to_layer.get(dst_file)
        if not sl or not dl:
            continue
        classified += 1

        is_v, reason, sev = _classify(sl, dl)
        if is_v:
            violations.append(LayerViolation(src_file, sl, dst_file, dl, reason, sev))
            continue
        is_v, reason, sev = _extra_skip_layer_check(sl, dl)
        if is_v:
            violations.append(LayerViolation(src_file, sl, dst_file, dl, reason, sev))

    total = len(graph.edges) or 1
    by_sev: dict[str, int] = {}
    for v in violations:
        by_sev[v.severity] = by_sev.get(v.severity, 0) + 1

    return {
        "violations": [v.__dict__ for v in violations],
        "summary": {
            "total_edges": len(graph.edges),
            "classified_edges": classified,
            "violation_count": len(violations),
            "violation_ratio": round(len(violations) / total, 3),
            "by_severity": by_sev,
            "layers_present": sorted({l for l in file_to_layer.values()}),
        },
    }


__all__ = [
    "LAYER_ORDER",
    "LAYER_ALIAS",
    "LayerViolation",
    "detect_layer_violations",
]
