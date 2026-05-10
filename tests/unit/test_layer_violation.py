"""分层违规检测单元测试。"""
from __future__ import annotations

from backend.engines.architecture.dependency_graph import (
    DependencyEdge,
    DependencyGraph,
    ModuleNode,
)
from backend.engines.architecture.layer_violation import detect_layer_violations


def _node(module_id: str, file_path: str) -> ModuleNode:
    return ModuleNode(module_id=module_id, file_path=file_path, language="python")


def _build_graph(files: list[str], edges: list[tuple[str, str]]) -> DependencyGraph:
    """辅助：按 src/dst 的 file_path 构造图。"""
    g = DependencyGraph()
    for f in files:
        mid = f.replace("/", ".").removesuffix(".py")
        g.nodes[mid] = _node(mid, f)
    for src, dst in edges:
        src_id = src.replace("/", ".").removesuffix(".py")
        dst_id = dst.replace("/", ".").removesuffix(".py")
        g.edges[(src_id, dst_id)] = DependencyEdge(src=src_id, dst=dst_id)
        g.adjacency[src_id].add(dst_id)
        g.reverse_adj[dst_id].add(src_id)
    return g


class TestLayerViolation:

    def test_healthy_flow_no_violation(self) -> None:
        files = [
            "controller/user.py",
            "service/user_service.py",
            "repository/user_repo.py",
        ]
        edges = [
            ("controller/user.py", "service/user_service.py"),
            ("service/user_service.py", "repository/user_repo.py"),
        ]
        result = detect_layer_violations(_build_graph(files, edges))
        assert result["summary"]["violation_count"] == 0

    def test_reverse_dependency_is_violation(self) -> None:
        files = [
            "controller/user.py",
            "service/user_service.py",
        ]
        edges = [
            # 反向：service 反过来依赖 controller
            ("service/user_service.py", "controller/user.py"),
        ]
        result = detect_layer_violations(_build_graph(files, edges))
        v = result["violations"]
        assert len(v) == 1
        assert v[0]["src_layer"] == "service"
        assert v[0]["dst_layer"] == "controller"
        assert "违反单向依赖约束" in v[0]["reason"]

    def test_skip_service_layer_warning(self) -> None:
        files = [
            "controller/order.py",
            "repository/order_repo.py",
        ]
        edges = [
            ("controller/order.py", "repository/order_repo.py"),
        ]
        result = detect_layer_violations(_build_graph(files, edges))
        v = result["violations"]
        assert len(v) == 1
        assert "跳过" in v[0]["reason"]
        assert v[0]["severity"] == "warning"

    def test_same_layer_ignored(self) -> None:
        files = [
            "service/a.py",
            "service/b.py",
        ]
        edges = [("service/a.py", "service/b.py")]
        result = detect_layer_violations(_build_graph(files, edges))
        assert result["summary"]["violation_count"] == 0

    def test_unclassified_file_ignored(self) -> None:
        files = [
            "utils/helper.py",
            "service/user_service.py",
        ]
        edges = [("utils/helper.py", "service/user_service.py")]
        result = detect_layer_violations(_build_graph(files, edges))
        # helper.py 不属于任何层，不产生违规
        assert result["summary"]["violation_count"] == 0

    def test_summary_fields(self) -> None:
        files = ["service/a.py", "controller/b.py"]
        edges = [("service/a.py", "controller/b.py")]
        result = detect_layer_violations(_build_graph(files, edges))
        s = result["summary"]
        assert s["total_edges"] == 1
        assert s["classified_edges"] == 1
        assert s["violation_count"] == 1
        assert s["violation_ratio"] == 1.0
        assert "controller" in s["layers_present"]
        assert "service" in s["layers_present"]
