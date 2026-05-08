"""
Markdown 报告渲染器。
"""
from __future__ import annotations


def render_markdown(data: dict) -> str:
    p = data["project"]
    v = data["version"]
    s = data["score"]
    m = data["metrics"]
    sev = data["severity_count"]

    lines: list[str] = []
    lines.append(f"# CodeGuard Pro 检测报告 — {p['name']}")
    lines.append("")
    lines.append(f"- 项目语言：**{p['language']}**")
    lines.append(f"- 版本标签：**{v['tag']}**")
    lines.append(f"- 文件总数：**{v['total_files']}**，有效代码行：**{v['total_lines']}**")
    lines.append(f"- 报告生成：**{data['generated_at']}**")
    lines.append("")

    lines.append("## 一、综合评分")
    lines.append("")
    lines.append(f"**综合得分：{s['overall']:.1f}（{s['grade']} 级）**")
    lines.append("")
    lines.append("| 维度 | 分数 |")
    lines.append("|---|---|")
    lines.append(f"| 规范度 | {s['spec']:.1f} |")
    lines.append(f"| 重复度 | {s['duplication']:.1f} |")
    lines.append(f"| 复杂度 | {s['complexity']:.1f} |")
    lines.append("")

    lines.append("## 二、执行摘要")
    lines.append("")
    lines.append(data["summary"])
    lines.append("")

    lines.append("## 三、关键指标")
    lines.append("")
    lines.append(f"- 总问题数：**{m['total_issues']}**")
    lines.append(f"  - 严重(error)：{sev.get('error', 0)}")
    lines.append(f"  - 警告(warning)：{sev.get('warning', 0)}")
    lines.append(f"  - 提示(info)：{sev.get('info', 0)}")
    lines.append(f"- 重复率：**{m['duplication_rate'] * 100:.2f}%**")
    lines.append(f"- 平均圈复杂度：**{m['avg_complexity']:.2f}**")
    lines.append(f"- 最高圈复杂度：**{m['max_complexity']}**")
    lines.append("")

    if data.get("top_files"):
        lines.append("## 四、问题热点文件 Top 10")
        lines.append("")
        lines.append("| # | 文件 | 问题数 |")
        lines.append("|---|---|---|")
        for i, f in enumerate(data["top_files"], 1):
            lines.append(f"| {i} | `{f['path']}` | {f['issues']} |")
        lines.append("")

    if data.get("complexity"):
        lines.append("## 五、复杂度热点 Top 30")
        lines.append("")
        lines.append("| 函数 | 文件 | 行数 | CC | 认知 | 嵌套 | 风险 |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in data["complexity"]:
            lines.append(
                f"| `{c['function_name']}` | `{c['file_path']}` | "
                f"{c['lines']} | {c['cyclomatic']} | {c['cognitive']} | "
                f"{c['nesting_depth']} | {c['risk_level']} |"
            )
        lines.append("")

    if data.get("duplications"):
        lines.append("## 六、重复代码块")
        lines.append("")
        for i, d in enumerate(data["duplications"], 1):
            lines.append(f"### 重复 #{i}")
            lines.append(f"- 检测方式：`{d['method']}`")
            lines.append(f"- 跨度：{d['line_length']} 行")
            lines.append("- 出现位置：")
            for o in d["occurrences"]:
                lines.append(f"  - `{o['file_path']}` 第 {o['start_line']} ~ {o['end_line']} 行")
            lines.append("")

    if data.get("top_rules"):
        lines.append("## 七、问题分布 — 触发最多的规则")
        lines.append("")
        lines.append("| 规则 | 触发次数 |")
        lines.append("|---|---|")
        for r in data["top_rules"]:
            lines.append(f"| `{r['rule_code']}` | {r['count']} |")
        lines.append("")

    if data.get("issues"):
        lines.append(f"## 八、详细问题清单（共 {len(data['issues'])} 条）")
        lines.append("")
        for idx, it in enumerate(data["issues"][:300], 1):
            lines.append(
                f"{idx}. **[{it['severity']}] {it['rule_code']}** "
                f"`{it['file_path']}:{it['line']}` — {it['message']}"
            )
            if it.get("suggestion"):
                lines.append(f"   - 修改建议：{it['suggestion']}")
        if len(data["issues"]) > 300:
            lines.append(f"\n> 仅展示前 300 条，剩余 {len(data['issues']) - 300} 条详见前端 / HTML 报告。\n")

    lines.append("")
    lines.append("---")
    lines.append("*由 CodeGuard Pro · 智能代码质量管理与规范检测平台 自动生成*")
    return "\n".join(lines)
