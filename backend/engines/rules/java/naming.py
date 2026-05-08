"""
Java 命名规范规则（JA-N001 ~ JA-N005）。

参考 Oracle Java Code Conventions 与 Google Java Style Guide。
"""
from __future__ import annotations

import re

import javalang
from javalang.tree import (
    ClassDeclaration,
    FieldDeclaration,
    InterfaceDeclaration,
    LocalVariableDeclaration,
    MethodDeclaration,
)

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

_RE_PASCAL = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_RE_CAMEL = re.compile(r"^[a-z][a-zA-Z0-9]*$")
_RE_UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_RE_PACKAGE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")

_ALLOWED_SHORT_VARS = {"i", "j", "k", "n", "x", "y", "z", "e", "ex"}


@register
class JavaClassNamingRule(Rule):
    code = "JA-N001"
    language = "java"
    category = "naming"
    severity = "error"
    name = "类/接口名应使用 PascalCase"
    description = "Java 类、接口、枚举名应采用 PascalCase 命名。"
    suggestion_template = "将类名改为 PascalCase，例如 UserService。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for cls in (ClassDeclaration, InterfaceDeclaration):
            for _, node in parsed.ast_root.filter(cls):
                if not _RE_PASCAL.match(node.name):
                    line = node.position.line if node.position else 1
                    issues.append(self.make_issue(
                        line=line,
                        message=f"类/接口名 '{node.name}' 不符合 PascalCase",
                        code_snippet=Rule.get_line_snippet(parsed, line),
                    ))
        return issues


@register
class JavaMethodNamingRule(Rule):
    code = "JA-N002"
    language = "java"
    category = "naming"
    severity = "warning"
    name = "方法名应使用 camelCase"
    description = "Java 方法名应采用 camelCase 命名（首字母小写）。"
    suggestion_template = "将方法名改为 camelCase，例如 calculateTotal。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(MethodDeclaration):
            if not _RE_CAMEL.match(node.name):
                line = node.position.line if node.position else 1
                issues.append(self.make_issue(
                    line=line,
                    message=f"方法名 '{node.name}' 不符合 camelCase",
                    code_snippet=Rule.get_line_snippet(parsed, line),
                ))
        return issues


@register
class JavaConstantNamingRule(Rule):
    code = "JA-N003"
    language = "java"
    category = "naming"
    severity = "warning"
    name = "常量（static final）应使用 UPPER_SNAKE_CASE"
    description = "static final 字段应采用全大写下划线命名。"
    suggestion_template = "改为 UPPER_SNAKE_CASE，例如 MAX_RETRY。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(FieldDeclaration):
            mods = node.modifiers or set()
            if "static" in mods and "final" in mods:
                for d in node.declarators:
                    if not _RE_UPPER_SNAKE.match(d.name):
                        line = node.position.line if node.position else 1
                        issues.append(self.make_issue(
                            line=line,
                            message=f"常量 '{d.name}' 应使用 UPPER_SNAKE_CASE",
                            code_snippet=Rule.get_line_snippet(parsed, line),
                        ))
        return issues


@register
class JavaPackageNamingRule(Rule):
    code = "JA-N004"
    language = "java"
    category = "naming"
    severity = "warning"
    name = "包名应全部小写"
    description = "Java 包名应采用全小写、点号分隔的形式。"
    suggestion_template = "将 package 名改为全小写，例如 com.example.app。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None or not parsed.ast_root.package:
            return issues
        pkg = parsed.ast_root.package
        name = pkg.name
        if not _RE_PACKAGE.match(name):
            line = pkg.position.line if pkg.position else 1
            issues.append(self.make_issue(
                line=line,
                message=f"包名 '{name}' 不符合全小写规范",
                code_snippet=Rule.get_line_snippet(parsed, line),
            ))
        return issues


@register
class JavaSingleLetterVarRule(Rule):
    code = "JA-N005"
    language = "java"
    category = "naming"
    severity = "info"
    name = "避免使用单字母变量"
    description = "除循环变量与异常变量外，不应使用单字母局部变量。"
    suggestion_template = "改用更具描述性的名称，例如 userCount。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        if parsed.ast_root is None:
            return issues
        for _, node in parsed.ast_root.filter(LocalVariableDeclaration):
            for d in node.declarators:
                if len(d.name) == 1 and d.name not in _ALLOWED_SHORT_VARS:
                    line = node.position.line if node.position else 1
                    issues.append(self.make_issue(
                        line=line,
                        message=f"避免单字母变量 '{d.name}'",
                        code_snippet=Rule.get_line_snippet(parsed, line),
                    ))
        return issues
