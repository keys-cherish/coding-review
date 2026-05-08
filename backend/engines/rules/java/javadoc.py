"""
Java Javadoc 规则（JA-C001 ~ JA-C003）。
"""
from __future__ import annotations

import re

from javalang.tree import ClassDeclaration, InterfaceDeclaration, MethodDeclaration

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


def _has_javadoc_above(parsed: ParsedFile, line: int) -> tuple[bool, int]:
    """检查指定行上方是否存在 Javadoc 块；若有，返回 (True, 起始行)。"""
    if line <= 1:
        return False, 0
    for i in range(line - 2, max(line - 50, -1), -1):
        if i < 0 or i >= parsed.total_lines:
            break
        stripped = parsed.raw_lines[i].strip()
        if not stripped or stripped.startswith("@"):
            continue
        if stripped.endswith("*/"):
            for j in range(i, max(i - 50, -1), -1):
                if "/**" in parsed.raw_lines[j]:
                    return True, j + 1
            return False, 0
        return False, 0
    return False, 0


def _javadoc_text(parsed: ParsedFile, start_line: int, end_line: int) -> str:
    """提取 Javadoc 块的文本（含 @标签）。"""
    return "\n".join(parsed.raw_lines[start_line - 1:end_line])


@register
class JavaPublicClassJavadocRule(Rule):
    code = "JA-C001"
    language = "java"
    category = "comment"
    severity = "warning"
    name = "公开类应有 Javadoc"
    description = "所有 public 类、接口应配备 Javadoc 说明。"
    suggestion_template = "在类定义前添加 /** 类的职责说明 */。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for cls in (ClassDeclaration, InterfaceDeclaration):
            for _, node in parsed.ast_root.filter(cls):
                if "public" not in (node.modifiers or set()):
                    continue
                line = node.position.line if node.position else 1
                ok, _ = _has_javadoc_above(parsed, line)
                if not ok:
                    issues.append(self.make_issue(
                        line=line,
                        message=f"公开类/接口 '{node.name}' 缺少 Javadoc",
                        code_snippet=Rule.get_line_snippet(parsed, line),
                    ))
        return issues


@register
class JavaPublicMethodJavadocRule(Rule):
    code = "JA-C002"
    language = "java"
    category = "comment"
    severity = "info"
    name = "公开方法应有 Javadoc"
    description = "public 方法应有 Javadoc 说明用途。"
    suggestion_template = "在方法定义前添加 /** 方法说明 */。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(MethodDeclaration):
            mods = node.modifiers or set()
            if "public" not in mods:
                continue
            # Override 的方法可豁免（具体可在配置中关闭）
            if any(getattr(a, "name", "") == "Override" for a in (node.annotations or [])):
                continue
            line = node.position.line if node.position else 1
            ok, _ = _has_javadoc_above(parsed, line)
            if not ok:
                issues.append(self.make_issue(
                    line=line,
                    message=f"公开方法 '{node.name}' 缺少 Javadoc",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                ))
        return issues


@register
class JavaJavadocTagRule(Rule):
    code = "JA-C003"
    language = "java"
    category = "comment"
    severity = "info"
    name = "Javadoc 应包含 @param/@return"
    description = "有参数的方法 Javadoc 应包含 @param；非 void 方法应包含 @return。"
    suggestion_template = "为每个参数添加 @param，非 void 方法添加 @return。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(MethodDeclaration):
            mods = node.modifiers or set()
            if "public" not in mods:
                continue
            line = node.position.line if node.position else 1
            ok, start = _has_javadoc_above(parsed, line)
            if not ok or start == 0:
                continue
            text = _javadoc_text(parsed, start, line - 1)
            params = node.parameters or []
            for p in params:
                if not re.search(rf"@param\s+{re.escape(p.name)}\b", text):
                    issues.append(self.make_issue(
                        line=line,
                        message=f"方法 '{node.name}' 的 Javadoc 缺少 @param {p.name}",
                        code_snippet=Rule.get_line_snippet(parsed, line),
                    ))
            return_type = getattr(node, "return_type", None)
            if return_type is not None and "@return" not in text:
                issues.append(self.make_issue(
                    line=line,
                    message=f"方法 '{node.name}' 的 Javadoc 缺少 @return",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                ))
        return issues
