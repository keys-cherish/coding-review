"""ORM 模型集中导出。

通过本模块的导入触发所有模型注册到 Base.metadata，
方便 init_database 一次建表。
"""
from backend.models.complexity_metric import ComplexityMetric
from backend.models.duplication import Duplication
from backend.models.issue import Issue, Severity
from backend.models.project import Project
from backend.models.report import Report
from backend.models.rule import Rule
from backend.models.scan_task import ScanTask, ScanTaskStatus
from backend.models.source_file import SourceFile
from backend.models.version import Version

__all__ = [
    "ComplexityMetric",
    "Duplication",
    "Issue",
    "Severity",
    "Project",
    "Report",
    "Rule",
    "ScanTask",
    "ScanTaskStatus",
    "SourceFile",
    "Version",
]
