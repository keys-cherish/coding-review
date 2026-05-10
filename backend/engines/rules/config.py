"""配置文件规则。"""
from __future__ import annotations

import re

from backend.engines.parser import ParsedFile
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

_SECRET_KEY_RE = re.compile(
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential)",
    re.I,
)
_PLACEHOLDER_RE = re.compile(r"\$\{[^}]+}|%\([^)]+\)s|<[^>]+>|changeme|your[_-]?", re.I)
_WEAK_VALUE_RE = re.compile(r"^(?:admin|root|password|passwd|secret|123456|test|demo|default)$", re.I)
_DEBUG_KEY_RE = re.compile(r"(?:debug|devtools|trace|verbose|show[_-]?sql)", re.I)
_TRUE_RE = re.compile(r"^(?:true|1|yes|on|enabled)$", re.I)
_INSECURE_URL_RE = re.compile(r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)", re.I)
_PERMISSIVE_ORIGIN_RE = re.compile(r"(?:allowed[_-]?origins|cors|origin)", re.I)


@register
class ConfigSyntaxRule(Rule):
    code = "CFG-SYN001"
    language = "config"
    category = "config"
    severity = "error"
    name = "配置文件语法错误"
    description = "检测 JSON/TOML/INI 等配置文件的基础语法错误。"
    suggestion_template = "修正配置文件语法后再提交扫描。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        if not parsed.parse_error:
            return []
        return [self.make_issue(
            1,
            f"配置文件解析失败：{parsed.parse_error}",
            code_snippet=self.get_line_snippet(parsed, 1),
        )]


@register
class ConfigSecretRule(Rule):
    code = "CFG-SEC001"
    language = "config"
    category = "security"
    severity = "error"
    name = "疑似硬编码敏感配置"
    description = "检测配置文件中疑似明文密码、令牌、密钥等敏感值。"
    suggestion_template = "将敏感值迁移到环境变量或密钥管理服务，仓库中仅保留占位符。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, key, value, raw in _iter_assignments(parsed):
            if not _SECRET_KEY_RE.search(key):
                continue
            cleaned = _clean_value(value)
            if not cleaned or _PLACEHOLDER_RE.search(cleaned):
                continue
            issues.append(self.make_issue(
                line_no,
                f"配置项 {key} 疑似包含硬编码敏感值",
                code_snippet=raw.strip(),
            ))
        return issues


@register
class ConfigWeakSecretRule(Rule):
    code = "CFG-SEC002"
    language = "config"
    category = "security"
    severity = "warning"
    name = "弱口令/默认密钥"
    description = "检测配置文件中的弱口令、默认口令或示例密钥值。"
    suggestion_template = "改用随机强密钥，并避免在配置文件中提交真实凭据。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, key, value, raw in _iter_assignments(parsed):
            cleaned = _clean_value(value)
            if _SECRET_KEY_RE.search(key) and _WEAK_VALUE_RE.match(cleaned):
                issues.append(self.make_issue(
                    line_no,
                    f"配置项 {key} 使用了弱口令或默认值",
                    code_snippet=raw.strip(),
                ))
        return issues


@register
class ConfigDebugRule(Rule):
    code = "CFG-ENV001"
    language = "config"
    category = "config"
    severity = "warning"
    name = "调试配置开启"
    description = "检测 debug/trace/verbose 等调试开关是否被开启。"
    suggestion_template = "生产配置中关闭调试与详细日志开关。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, key, value, raw in _iter_assignments(parsed):
            if _DEBUG_KEY_RE.search(key) and _TRUE_RE.match(_clean_value(value)):
                issues.append(self.make_issue(
                    line_no,
                    f"配置项 {key} 开启了调试/跟踪能力",
                    code_snippet=raw.strip(),
                ))
        return issues


@register
class ConfigInsecureEndpointRule(Rule):
    code = "CFG-SEC003"
    language = "config"
    category = "security"
    severity = "warning"
    name = "不安全的明文 HTTP 地址"
    description = "检测非本地地址使用 http:// 明文协议。"
    suggestion_template = "外部服务地址优先使用 HTTPS，并确认传输链路加密。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, raw in enumerate(parsed.raw_lines, start=1):
            if _INSECURE_URL_RE.search(raw):
                issues.append(self.make_issue(
                    line_no,
                    "配置中包含非本地明文 HTTP 地址",
                    code_snippet=raw.strip(),
                ))
        return issues


@register
class ConfigPermissiveCorsRule(Rule):
    code = "CFG-SEC004"
    language = "config"
    category = "security"
    severity = "warning"
    name = "过宽的跨域配置"
    description = "检测 CORS/Origin 配置是否放开为星号。"
    suggestion_template = "将跨域白名单限制为可信域名，避免使用 '*'。"

    def check(self, parsed: ParsedFile) -> list[Issue]:
        issues: list[Issue] = []
        for line_no, key, value, raw in _iter_assignments(parsed):
            if _PERMISSIVE_ORIGIN_RE.search(key) and "*" in value:
                issues.append(self.make_issue(
                    line_no,
                    f"配置项 {key} 允许任意来源访问",
                    code_snippet=raw.strip(),
                ))
        return issues


def _iter_assignments(parsed: ParsedFile):
    for line_no, raw in enumerate(parsed.raw_lines, start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(("#", "//", ";")):
            continue
        match = re.match(r'^[\s"\']*([A-Za-z0-9_.-]+)[\s"\']*(?:=|:)[\s"\']*(.+?)[\s,]*$', raw)
        if match:
            yield line_no, match.group(1), match.group(2), raw


def _clean_value(value: str) -> str:
    return value.strip().strip('"\'').rstrip(",")
