"""
架构分析引擎：依赖图、循环依赖、架构模式识别、六维雷达。
"""
from backend.engines.architecture.dependency_graph import (
    DependencyGraph,
    DependencyEdge,
    ModuleNode,
    build_dependency_graph,
)
from backend.engines.architecture.cycle_detector import (
    detect_cycles,
    CycleInfo,
)
from backend.engines.architecture.pattern_recognizer import (
    ArchPattern,
    recognize_architecture,
)
from backend.engines.architecture.arch_scorer import (
    ArchDimensionScore,
    compute_arch_radar,
)
from backend.engines.architecture.call_graph import (
    CallGraph,
    build_call_graph,
)
from backend.engines.architecture.uml_extractor import (
    UMLClass,
    UMLField,
    UMLMethod,
    extract_uml_classes,
    render_mermaid_class_diagram,
    render_plantuml_class_diagram,
)

__all__ = [
    "DependencyGraph",
    "DependencyEdge",
    "ModuleNode",
    "build_dependency_graph",
    "detect_cycles",
    "CycleInfo",
    "ArchPattern",
    "recognize_architecture",
    "ArchDimensionScore",
    "compute_arch_radar",
    "CallGraph",
    "build_call_graph",
    "UMLClass",
    "UMLField",
    "UMLMethod",
    "extract_uml_classes",
    "render_mermaid_class_diagram",
    "render_plantuml_class_diagram",
]
