"""配置文件扫描单元测试。"""
from __future__ import annotations

from pathlib import Path

from backend.engines.parser import parse_file
from backend.engines.rules import RuleEngine
from backend.engines.rules.registry import discover_rules, rule_registry
from backend.services.upload_service import collect_source_files
from backend.utils.file_utils import detect_language


def test_detect_language_for_config_files() -> None:
    assert detect_language("application.yml") == "config"
    assert detect_language("pyproject.toml") == "config"
    assert detect_language(".env") == "config"


def test_collect_source_files_includes_config_for_python_project(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "application.yml").write_text("debug: true\n", encoding="utf-8")

    entries = collect_source_files(tmp_path, "python")
    rels = {entry[1]: entry[2] for entry in entries}

    assert rels["app.py"] == "python"
    assert rels["application.yml"] == "config"


def test_config_parser_reports_json_syntax_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"debug": true,}', encoding="utf-8")

    parsed = parse_file(path)

    assert parsed.language == "config"
    assert parsed.parse_error


def test_parse_file_detects_dotenv_by_name(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("SECRET_KEY=dev-secret\n", encoding="utf-8")

    parsed = parse_file(path)

    assert parsed.language == "config"
    assert not parsed.parse_error


def test_config_rules_detect_security_and_environment_issues(tmp_path: Path) -> None:
    discover_rules()
    path = tmp_path / "application.yml"
    path.write_text(
        "debug: true\n"
        "password: admin\n"
        "api_key: real-token-value\n"
        "service_url: http://example.com/api\n"
        "allowed_origins: '*'\n",
        encoding="utf-8",
    )
    parsed = parse_file(path)

    issues = RuleEngine().check_file(parsed)
    codes = {issue.rule_code for issue in issues}

    assert "CFG-ENV001" in codes
    assert "CFG-SEC001" in codes
    assert "CFG-SEC002" in codes
    assert "CFG-SEC003" in codes
    assert "CFG-SEC004" in codes
    assert any(rule.language == "config" for rule in rule_registry.all_rules())
