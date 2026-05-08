"""
PDF 报告渲染器（基于 WeasyPrint，可选）。

本模块属于"软依赖"——若环境未安装 WeasyPrint 或 GTK，
report_service 会自动降级为 HTML 报告，不影响主流程。
"""
from __future__ import annotations

from pathlib import Path

from backend.reports.html_renderer import render_html


def render_pdf(data: dict, output_path: Path) -> Path:
    """渲染 PDF。若失败抛异常，由调用方决定降级策略。"""
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "未安装 WeasyPrint。请使用浏览器打印 HTML 报告为 PDF，"
            "或参考 https://weasyprint.org 安装。"
        ) from e

    html_content = render_html(data)
    HTML(string=html_content).write_pdf(str(output_path))
    return output_path
