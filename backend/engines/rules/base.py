"""
规则基类与公共数据结构。

每条规则都是一个继承 Rule 的类，通过装饰器自动注册到 RuleRegistry。
规则只关心"如何检测"，不关心"何时被调用"，由 RuleEngine 编排。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from backend.engines.parser import ParsedFile


@dataclass
class Issue:
    """规则发现的问题。

    与 ORM Issue 模型字段对齐，由 ScanOrchestrator 转换为 ORM 对象写库。
    """
    rule_code: str
    category: str
    severity: str  # error / warning / info
    line: int
    column: int = 0
    end_line: int = 0
    message: str = ""
    code_snippet: str = ""
    suggestion: str = ""

    def __post_init__(self) -> None:
        if self.end_line == 0:
            self.end_line = self.line


class Rule(ABC):
    """规则抽象基类。

    子类至少要设置 code/language/category/severity/name/description，
    并实现 check()。
    """

    # ---------- 元数据（子类必须覆盖） ----------
    code: ClassVar[str] = ""
    language: ClassVar[str] = ""        # python / java
    category: ClassVar[str] = ""        # naming / indent / comment / space / magic / dead / import / length / complex
    severity: ClassVar[str] = "warning"
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    suggestion_template: ClassVar[str] = ""

    # ---------- 运行期 ----------
    enabled: bool = True
    config: dict = field(default_factory=dict)  # type: ignore[assignment]

    def __init__(self) -> None:
        self.config = {}

    @abstractmethod
    def check(self, parsed: ParsedFile) -> list[Issue]:
        """实施检测，返回该规则在该文件上发现的所有问题。"""

    # ---------- 工具 ----------
    def make_issue(
        self,
        line: int,
        message: str,
        *,
        column: int = 0,
        end_line: int = 0,
        code_snippet: str = "",
        suggestion: str = "",
    ) -> Issue:
        """便捷构造 Issue。"""
        return Issue(
            rule_code=self.code,
            category=self.category,
            severity=self.severity,
            line=line,
            column=column,
            end_line=end_line or line,
            message=message,
            code_snippet=code_snippet,
            suggestion=suggestion or self.suggestion_template,
        )

    @staticmethod
    def get_line_snippet(parsed: ParsedFile, line: int, context: int = 0) -> str:
        """获取指定行（或带上下文）的源码片段。"""
        if line < 1 or line > parsed.total_lines:
            return ""
        start = max(0, line - 1 - context)
        end = min(parsed.total_lines, line + context)
        return "\n".join(parsed.raw_lines[start:end])
