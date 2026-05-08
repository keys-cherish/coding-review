"""
问题与规则相关 Pydantic 模型。
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_task_id: int
    source_file_id: int
    rule_code: str
    category: str
    severity: str
    line: int
    column: int
    end_line: int
    message: str
    code_snippet: str | None = None
    suggestion: str | None = None


class IssueWithFile(IssueOut):
    file_path: str


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    language: str
    category: str
    name: str
    description: str
    severity: str
    enabled: bool


class RuleToggle(BaseModel):
    enabled: bool


class ComplexityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    function_name: str
    start_line: int
    end_line: int
    lines: int
    cyclomatic: int
    cognitive: int
    nesting_depth: int
    parameters: int
    risk_level: str


class DuplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fingerprint: str
    token_length: int
    line_length: int
    occurrences: int
    detection_method: str
    occurrences_json: str
