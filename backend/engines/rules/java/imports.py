"""
Java import 规则（JA-IM001）。
"""
from __future__ import annotations

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


@register
class JavaWildcardImportRule(Rule):
    code = "JA-IM001"
    language = "java"
    category = "import"
    severity = "warning"
    name = "禁止通配符 import"
    description = "import 不应使用 .* 通配符，明确导入需要的类型。"
    suggestion_template = "改为显式导入需要的类，例如 import java.util.List;"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None or not parsed.ast_root.imports:
            return issues
        for imp in parsed.ast_root.imports:
            if imp.wildcard:
                line = imp.position.line if imp.position else 1
                issues.append(self.make_issue(
                    line=line,
                    message=f"通配符 import: {imp.path}.*",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                ))
        return issues
