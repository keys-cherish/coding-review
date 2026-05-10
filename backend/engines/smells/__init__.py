"""
代码"坏味道"检测器 — 上帝类 / 上帝方法 / 胖接口 / 过长参数列表。

设计要点
--------
- 与具体语言解耦：输入统一 `ParsedFile`，不直接碰 AST
- 每种坏味道给出 Issue 列表；调用方自选启用哪些
- 阈值可通过 settings / rule.config 覆盖
- 判定结果稳定可重现，便于写测试

阈值默认值（参考经验值 & Martin Fowler《重构》）
    上帝类:
        类方法数 > 20 或 类行数 > 400 或 类字段数 > 20
    胖接口:
        抽象方法数 > 15
    上帝方法:
        函数行数 > 80 或 圈复杂度 > 15
    过长参数列表:
        参数数量 > 5
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable

from backend.engines.parser import ClassInfo, FunctionInfo, ParsedFile
from backend.engines.rules.base import Issue


# ---------- 阈值 ----------

@dataclass
class SmellThresholds:
    god_class_methods: int = 20
    god_class_lines: int = 400
    god_class_fields: int = 20
    fat_interface_methods: int = 15
    god_method_lines: int = 80
    god_method_cc: int = 15
    long_parameter_list: int = 5


DEFAULT_THRESHOLDS = SmellThresholds()


# ---------- 公共计算 ----------

def _count_class_fields_python(cls: ClassInfo) -> int:
    node = cls.raw_node
    if not isinstance(node, ast.ClassDef):
        return 0
    fields: set[str] = set()

    # 类级变量声明
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fields.add(stmt.target.id)
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name):
                    fields.add(t.id)

    # __init__ 中 self.x = ... 的字段
    for m in node.body:
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == "__init__":
            for sub in ast.walk(m):
                if isinstance(sub, ast.Assign):
                    for tgt in sub.targets:
                        if (
                            isinstance(tgt, ast.Attribute)
                            and isinstance(tgt.value, ast.Name)
                            and tgt.value.id == "self"
                        ):
                            fields.add(tgt.attr)
    return len(fields)


def _count_class_fields_java(cls: ClassInfo) -> int:
    """javalang ClassDeclaration.fields 直接给出字段列表。"""
    node = cls.raw_node
    fields = getattr(node, "fields", None)
    if fields is None:
        return 0
    count = 0
    for f in fields:
        decls = getattr(f, "declarators", []) or []
        count += len(decls) or 1
    return count


def _count_class_fields(cls: ClassInfo, language: str) -> int:
    if language == "python":
        return _count_class_fields_python(cls)
    if language == "java":
        return _count_class_fields_java(cls)
    return 0


def _is_java_interface(cls: ClassInfo) -> bool:
    node = cls.raw_node
    # javalang 的 InterfaceDeclaration 和 ClassDeclaration 是不同类型
    return node is not None and type(node).__name__ == "InterfaceDeclaration"


def _python_function_cc(fn: FunctionInfo) -> int:
    """对一个 Python 函数计算 McCabe 圈复杂度。"""
    node = fn.raw_node
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 1
    cc = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
                          ast.With, ast.AsyncWith, ast.Assert, ast.IfExp)):
            cc += 1
        elif isinstance(n, ast.BoolOp):
            cc += max(0, len(n.values) - 1)
        elif isinstance(n, ast.comprehension):
            cc += 1 + len(n.ifs)
        elif isinstance(n, ast.Match):
            cc += len(n.cases)
    return cc


def _java_function_cc(fn: FunctionInfo) -> int:
    """基于 javalang 节点粗估圈复杂度。"""
    node = fn.raw_node
    if node is None:
        return 1
    cc = 1
    # javalang 节点可迭代所有子节点
    try:
        from javalang.tree import (
            IfStatement, ForStatement, WhileStatement, DoStatement,
            SwitchStatementCase, CatchClause, TernaryExpression,
        )
    except Exception:
        return 1
    for _, sub in node:  # type: ignore[call-overload]
        if isinstance(sub, (IfStatement, ForStatement, WhileStatement, DoStatement,
                            CatchClause, TernaryExpression)):
            cc += 1
        elif isinstance(sub, SwitchStatementCase):
            cc += 1
    return cc


def _function_cc(fn: FunctionInfo, language: str) -> int:
    if language == "python":
        return _python_function_cc(fn)
    if language == "java":
        return _java_function_cc(fn)
    return 1


# ---------- 检测器 ----------

def _methods_of(cls: ClassInfo, parsed: ParsedFile) -> list[FunctionInfo]:
    """收集属于该类的方法。

    Python 解析器将类方法放入 parsed.functions（qualified_name 带类名前缀），
    Java 解析器则填入 cls.methods。这里统一处理。
    """
    if cls.methods:
        return list(cls.methods)
    prefix = cls.qualified_name + "." if cls.qualified_name else cls.name + "."
    return [
        fn for fn in parsed.functions
        if fn.qualified_name.startswith(prefix)
        and cls.start_line <= fn.start_line <= cls.end_line
    ]


def detect_god_classes(parsed: ParsedFile, th: SmellThresholds = DEFAULT_THRESHOLDS) -> list[Issue]:
    issues: list[Issue] = []
    for cls in parsed.classes:
        if _is_java_interface(cls):
            continue
        methods = _methods_of(cls, parsed)
        method_count = len(methods)
        line_count = max(0, cls.end_line - cls.start_line + 1)
        field_count = _count_class_fields(cls, parsed.language)

        reasons: list[str] = []
        if method_count > th.god_class_methods:
            reasons.append(f"方法数 {method_count} > {th.god_class_methods}")
        if line_count > th.god_class_lines:
            reasons.append(f"类行数 {line_count} > {th.god_class_lines}")
        if field_count > th.god_class_fields:
            reasons.append(f"字段数 {field_count} > {th.god_class_fields}")

        if not reasons:
            continue

        severity = "error" if len(reasons) >= 2 else "warning"
        issues.append(Issue(
            rule_code="SMELL-GOD-CLASS",
            category="smell",
            severity=severity,
            line=cls.start_line,
            end_line=cls.end_line,
            message=f"上帝类 {cls.name}：{'；'.join(reasons)}",
            suggestion="按单一职责原则拆分成多个更小的类（提取子类 / 提取委托 / 提取策略）",
        ))
    return issues


def detect_fat_interfaces(parsed: ParsedFile, th: SmellThresholds = DEFAULT_THRESHOLDS) -> list[Issue]:
    if parsed.language != "java":
        return []
    issues: list[Issue] = []
    for cls in parsed.classes:
        if not _is_java_interface(cls):
            continue
        m = len(cls.methods)
        if m > th.fat_interface_methods:
            issues.append(Issue(
                rule_code="SMELL-FAT-INTERFACE",
                category="smell",
                severity="warning",
                line=cls.start_line,
                end_line=cls.end_line,
                message=f"胖接口 {cls.name}：方法数 {m} > {th.fat_interface_methods}",
                suggestion="按接口隔离原则（ISP）拆为多个职责单一的小接口",
            ))
    return issues


def detect_god_methods(parsed: ParsedFile, th: SmellThresholds = DEFAULT_THRESHOLDS) -> list[Issue]:
    """检测方法行数过长 / 圈复杂度过高。"""
    issues: list[Issue] = []
    all_fns: Iterable[FunctionInfo] = list(parsed.functions)
    for cls in parsed.classes:
        all_fns = list(all_fns) + list(cls.methods)

    seen: set[tuple[str, int]] = set()
    for fn in all_fns:
        key = (fn.qualified_name, fn.start_line)
        if key in seen:
            continue
        seen.add(key)

        lines = max(0, fn.end_line - fn.start_line + 1)
        cc = _function_cc(fn, parsed.language)

        reasons: list[str] = []
        if lines > th.god_method_lines:
            reasons.append(f"函数 {lines} 行 > {th.god_method_lines}")
        if cc > th.god_method_cc:
            reasons.append(f"圈复杂度 {cc} > {th.god_method_cc}")

        if not reasons:
            continue

        issues.append(Issue(
            rule_code="SMELL-GOD-METHOD",
            category="smell",
            severity="warning",
            line=fn.start_line,
            end_line=fn.end_line,
            message=f"上帝方法 {fn.name}：{'；'.join(reasons)}",
            suggestion="提取子方法（Extract Method），或用策略/状态模式拆分分支",
        ))
    return issues


def detect_long_parameter_lists(parsed: ParsedFile, th: SmellThresholds = DEFAULT_THRESHOLDS) -> list[Issue]:
    issues: list[Issue] = []
    candidates: list[FunctionInfo] = list(parsed.functions)
    for cls in parsed.classes:
        candidates += list(cls.methods)

    seen: set[tuple[str, int]] = set()
    for fn in candidates:
        key = (fn.qualified_name, fn.start_line)
        if key in seen:
            continue
        seen.add(key)

        n = len(fn.parameters)
        # Python 里 self/cls 不算
        params = [p for p in fn.parameters if p not in ("self", "cls")]
        n = len(params)
        if n > th.long_parameter_list:
            issues.append(Issue(
                rule_code="SMELL-LONG-PARAM-LIST",
                category="smell",
                severity="info",
                line=fn.start_line,
                end_line=fn.start_line,
                message=f"参数过多：{fn.name}({n} 个参数 > {th.long_parameter_list})",
                suggestion="引入参数对象（Introduce Parameter Object）或 Builder 模式",
            ))
    return issues


def detect_all_smells(parsed: ParsedFile, th: SmellThresholds = DEFAULT_THRESHOLDS) -> list[Issue]:
    return [
        *detect_god_classes(parsed, th),
        *detect_fat_interfaces(parsed, th),
        *detect_god_methods(parsed, th),
        *detect_long_parameter_lists(parsed, th),
    ]
