"""
Python 空格相关规则（PY-S001 ~ PY-S003）。
"""
from __future__ import annotations

import re

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register


# 二元运算符两侧应有空格（不在字符串/注释里）
_BAD_BINOP = re.compile(r"[A-Za-z0-9_\)\]](=|==|!=|<=|>=|\+=|-=|\*=|/=|\+|-(?!\d)|\*|/|%|<|>)[A-Za-z0-9_\(]")
_BAD_COMMA = re.compile(r",[A-Za-z0-9_\(\[]")


def _strip_strings_and_comments(line: str) -> str:
    """简单去掉字符串字面量和注释，避免误报。"""
    out: list[str] = []
    i = 0
    n = len(line)
    in_str = None
    while i < n:
        ch = line[i]
        if in_str:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            i += 1
            continue
        if ch == "#":
            break
        out.append(ch)
        i += 1
    return "".join(out)


@register
class BinaryOperatorSpaceRule(Rule):
    code = "PY-S001"
    language = "python"
    category = "space"
    severity = "info"
    name = "二元运算符两侧应有空格"
    description = "形如 a=b 的写法应改为 a = b（赋值/算术/比较运算符两侧都应有空格）。"
    suggestion_template = "在运算符两侧各加一个空格，例如 a = b。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            cleaned = _strip_strings_and_comments(raw)
            # 默认参数 / 关键字参数 形式 a=1 是允许的，简化策略：
            # 仅在等号两侧紧贴字母数字时报告，且不在 () 内的位置才报
            if "(" in cleaned and ")" in cleaned:
                continue
            m = _BAD_BINOP.search(cleaned)
            if m:
                issues.append(self.make_issue(
                    line=line_no,
                    column=m.start(),
                    message="运算符两侧缺少空格",
                    code_snippet=raw[:80],
                ))
        return issues


@register
class CommaSpaceRule(Rule):
    code = "PY-S002"
    language = "python"
    category = "space"
    severity = "info"
    name = "逗号后应有空格"
    description = "逗号后应紧跟一个空格，例如 (a, b) 而非 (a,b)。"
    suggestion_template = "在逗号后添加一个空格。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            cleaned = _strip_strings_and_comments(raw)
            m = _BAD_COMMA.search(cleaned)
            if m:
                issues.append(self.make_issue(
                    line=line_no,
                    column=m.start(),
                    message="逗号后应有一个空格",
                    code_snippet=raw[:80],
                ))
        return issues


@register
class TopLevelBlankLineRule(Rule):
    code = "PY-S003"
    language = "python"
    category = "space"
    severity = "info"
    name = "顶层函数/类定义之间应空两行"
    description = "PEP 8 规定模块顶层 def/class 之间应空两行。"
    suggestion_template = "在两个顶层定义之间补足两行空行。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        body = list(parsed.ast_root.body)
        for i in range(1, len(body)):
            prev = body[i - 1]
            cur = body[i]
            import ast
            if not isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            prev_end = getattr(prev, "end_lineno", prev.lineno) or prev.lineno
            gap = cur.lineno - prev_end - 1
            if gap < 2:
                issues.append(self.make_issue(
                    line=cur.lineno,
                    message=f"顶层定义前应空两行（当前 {gap} 行）",
                    code_snippet=Rule.get_line_snippet(parsed, cur.lineno),
                ))
        return issues
