"""
HTML 报告渲染器。
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_html(data: dict) -> str:
    """根据收集的数据渲染独立 HTML 报告。"""
    template = _env.get_template("report.html.jinja2")
    return template.render(**data)
