"""
Java 死代码 / 无效代码规则（JA-D001 ~ JA-D003）。
"""
from __future__ import annotations

import re

from javalang.tree import (
    BreakStatement,
    CatchClause,
    ContinueStatement,
    ReturnStatement,
    StatementExpression,
    ThrowStatement,
)

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class JavaUnusedImportRule(Rule):
    code = "JA-D001"
    language = "java"
    category = "dead"
    severity = "warning"
    name = "未使用的 import"
    description = "import 但未在文件中使用的类型应当移除。"
    suggestion_template = "删除未使用的 import 语句。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None or not parsed.ast_root.imports:
            return issues
        # 拼接所有非 import 行作为引用区
        body_lines: list[str] = []
        for raw in parsed.raw_lines:
            stripped = raw.strip()
            if stripped.startswith("import ") or stripped.startswith("package "):
                continue
            body_lines.append(raw)
        body_text = "\n".join(body_lines)

        for imp in parsed.ast_root.imports:
            if imp.wildcard or imp.static:
                continue
            short = imp.path.split(".")[-1]
            if not re.search(rf"\b{re.escape(short)}\b", body_text):
                line = imp.position.line if imp.position else 1
                issues.append(self.make_issue(
                    line=line,
                    message=f"未使用的 import: {imp.path}",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                ))
        return issues


@register
class JavaEmptyCatchRule(Rule):
    code = "JA-D002"
    language = "java"
    category = "dead"
    severity = "error"
    name = "禁止空 catch 块"
    description = "空的 catch 块会吞掉异常，使问题难以定位。"
    suggestion_template = "至少记录日志，或重新抛出异常，或写明忽略原因。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(CatchClause):
            block = node.block
            if not block:
                line = node.position.line if node.position else 1
                issues.append(self.make_issue(
                    line=line,
                    message="catch 块为空，会吞掉异常",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                ))
        return issues


@register
class JavaUnreachableAfterReturnRule(Rule):
    code = "JA-D003"
    language = "java"
    category = "dead"
    severity = "error"
    name = "return / throw / break / continue 后的不可达代码"
    description = "终止语句之后的代码永远不会执行。"
    suggestion_template = "删除终止语句之后的死代码。"

    _TERMINATORS = (ReturnStatement, ThrowStatement, BreakStatement, ContinueStatement)

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(self._TERMINATORS):
            # 简单启发式：在源码中向下找下一行非空非注释，若仍在同一 block 缩进就报告
            line = node.position.line if node.position else 0
            if line == 0:
                continue
            indent = len(parsed.raw_lines[line - 1]) - len(parsed.raw_lines[line - 1].lstrip())
            for n_line in range(line, min(line + 10, parsed.total_lines)):
                raw = parsed.raw_lines[n_line]
                stripped = raw.strip()
                if not stripped:
                    continue
                if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                    continue
                if stripped in ("}", "});", "} else {", "} catch (", "});"):
                    break
                cur_indent = len(raw) - len(raw.lstrip())
                if cur_indent >= indent and not stripped.startswith("}"):
                    issues.append(self.make_issue(
                        line=n_line + 1,
                        message="此语句之前已 return/throw/break/continue，不可达",
                        code_snippet=Rule.get_line_snippet(parsed, n_line + 1),
                    ))
                break
        return issues
