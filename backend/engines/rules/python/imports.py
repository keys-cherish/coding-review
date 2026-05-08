"""
Python import 规则（PY-IM001 ~ PY-IM003）。
"""
from __future__ import annotations

import ast
import sys

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

_STDLIB = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()


@register
class ImportAtTopRule(Rule):
    code = "PY-IM001"
    language = "python"
    category = "import"
    severity = "warning"
    name = "import 语句应位于文件顶部"
    description = "除运行时延迟导入（避免循环依赖）外，所有 import 应集中在文件开头。"
    suggestion_template = "将该 import 移至文件顶部其他 import 附近。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        body = parsed.ast_root.body
        seen_non_import = False
        for node in body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if seen_non_import:
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message="import 语句出现在非 import 语句之后",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
            else:
                # docstring/__future__ import 之外都视为非 import
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    continue
                seen_non_import = True
        return issues


@register
class WildcardImportRule(Rule):
    code = "PY-IM002"
    language = "python"
    category = "import"
    severity = "warning"
    name = "禁止使用 from X import *"
    description = "通配符导入会污染命名空间、降低可维护性。"
    suggestion_template = "改为显式导入需要的名称：from X import a, b, c。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for node in ast.walk(parsed.ast_root):
            if isinstance(node, ast.ImportFrom):
                if any(a.name == "*" for a in node.names):
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message=f"通配符 import: from {node.module} import *",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
        return issues


@register
class ImportGroupingRule(Rule):
    code = "PY-IM003"
    language = "python"
    category = "import"
    severity = "info"
    name = "import 应分组（标准库 / 三方 / 本地）"
    description = "import 应按 标准库 → 第三方 → 本地 顺序分组，组间空一行。"
    suggestion_template = "调整 import 顺序，按 标准库/三方/本地 分组并空行分隔。"

    def _classify(self, module: str) -> str:
        if not module:
            return "local"
        first = module.split(".")[0]
        if first in _STDLIB or first in {"typing_extensions"}:
            return "stdlib"
        if module.startswith(".") or first in {"backend", "frontend", "tests", "scripts", "cli"}:
            return "local"
        return "third"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        order = {"stdlib": 0, "third": 1, "local": 2}
        last_group = -1
        for node in parsed.ast_root.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                if last_group >= 0:
                    break
                continue
            if isinstance(node, ast.Import):
                modules = [a.name for a in node.names]
            else:
                modules = [node.module or ""]
            for m in modules:
                grp = order[self._classify(m)]
                if grp < last_group:
                    issues.append(self.make_issue(
                        line=node.lineno,
                        message=f"import {m} 顺序错误（应按 标准库/三方/本地 排列）",
                        code_snippet=Rule.get_line_snippet(parsed, node.lineno),
                    ))
                    return issues  # 一处提示即可
                last_group = grp
        return issues
