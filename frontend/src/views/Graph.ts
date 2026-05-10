/**
 * 文件依赖图（ECharts force）+ 循环依赖侧栏。
 *
 * - 节点按顶层目录分色，渐变球体 + 玻璃高光
 * - 在循环内的节点用红色 glow + 流动粒子标记
 * - 点击节点高亮 1 度邻居并在右侧显示详情
 */
import * as echarts from 'echarts';

import { visApi, type DepGraphPayload, type DepCycle } from '../api';
import { pageShell } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';
import {
    BRAND, INK_MUTED,
    SEVERITY, LAYER_PALETTE, pickLayer,
    radialGradient, linearGradient,
    chartBaseOption, legendStyle, toolboxBase,
    richTooltip, withAlpha,
} from '../utils/chartTheme';

const SEVERITY_HEX: Record<string, string> = {
    critical: SEVERITY.critical.from,
    high: SEVERITY.high.from,
    medium: SEVERITY.medium.from,
    low: SEVERITY.low.from,
};

export async function renderGraph(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '依赖关系图',
        subtitle: '文件/模块级依赖，力导向布局，自动识别循环依赖',
        body: `
            <div class="viz-toolbar" id="graph-toolbar"></div>

            <div class="graph-layout" style="margin-top:16px">
                <div class="card graph-main chart-glass">
                    <div class="chart-aurora aurora-graph"></div>
                    <div class="card-header">
                        <div class="card-title">模块依赖拓扑</div>
                        <div class="graph-legend-slot" id="graph-stat-chips"></div>
                    </div>
                    <div class="card-body" style="padding:0;position:relative">
                        <div id="dep-graph" style="height:660px;position:relative;z-index:1"></div>
                    </div>
                </div>

                <div class="graph-aside stack-v">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">循环依赖</div>
                            <div class="card-subtitle" id="cycle-count">—</div>
                        </div>
                        <div class="card-body" id="cycle-list"></div>
                    </div>

                    <div class="card">
                        <div class="card-header"><div class="card-title">节点详情</div></div>
                        <div class="card-body" id="node-detail">
                            <div class="empty-sm">点击左侧节点查看依赖关系</div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header"><div class="card-title">拓扑统计</div></div>
                        <div class="card-body" id="graph-stats"></div>
                    </div>
                </div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#graph-toolbar') as HTMLElement;
    const chartEl = container.querySelector('#dep-graph') as HTMLElement;
    const chart = echarts.init(chartEl);
    window.addEventListener('resize', () => chart.resize());

    await mountScanPicker(toolbar, async (scanId) => {
        chart.showLoading({ text: '构建依赖图...', maskColor: 'rgba(255,255,255,0.6)', textColor: BRAND });
        const { data, error } = await visApi.depGraph(scanId);
        chart.hideLoading();
        if (error || !data) {
            toast.error(error || '依赖图加载失败');
            return;
        }
        renderDepGraph(chart, data, container);
        renderCycles(container, data.cycles);
        renderStats(container, data);
        renderHeaderChips(container, data);
    });
}

function renderHeaderChips(container: HTMLElement, data: DepGraphPayload): void {
    const slot = container.querySelector('#graph-stat-chips') as HTMLElement;
    if (!slot) return;
    const cycleColor = data.cycles.length > 0 ? SEVERITY.high.from : SEVERITY.ok.from;
    slot.innerHTML = `
        <span class="head-chip"><span class="dot" style="background:${BRAND}"></span>${data.nodes.length} 节点</span>
        <span class="head-chip"><span class="dot" style="background:${LAYER_PALETTE[1]!.from}"></span>${data.links.length} 边</span>
        <span class="head-chip"><span class="dot" style="background:${cycleColor}"></span>${data.cycles.length} 循环</span>
    `;
}

function renderDepGraph(
    chart: echarts.ECharts,
    data: DepGraphPayload,
    container: HTMLElement,
): void {
    if (!data.nodes.length) {
        chart.clear();
        chart.setOption({
            graphic: {
                type: 'text',
                left: 'center', top: 'middle',
                style: { text: '暂无可分析的依赖关系', fontSize: 14, fill: '#a1a1aa' },
            },
        });
        return;
    }

    const categories = data.categories.map((c, i) => {
        const p = pickLayer(i);
        return {
            name: c.name,
            itemStyle: { color: linearGradient(p.from, p.to, 'd') },
        };
    });

    const nodes = data.nodes.map(n => {
        const cat = pickLayer(n.category);
        const baseColor = n.in_cycle ? SEVERITY.high.from : cat.from;
        const fill = n.in_cycle
            ? radialGradient('#fda4af', SEVERITY.critical.from)
            : radialGradient(cat.to, cat.from);
        return {
            id: n.id,
            name: n.name,
            value: n.loc,
            symbolSize: n.size,
            category: n.category,
            itemStyle: {
                color: fill,
                borderColor: n.in_cycle ? '#fee2e2' : 'rgba(255,255,255,0.85)',
                borderWidth: n.in_cycle ? 2.5 : 1.5,
                shadowBlur: n.in_cycle ? 20 : 10,
                shadowColor: n.in_cycle ? SEVERITY.high.glow : withAlpha(baseColor, 0.35),
            },
            label: {
                show: data.nodes.length <= 60 || n.size > 32,
                position: 'right',
                formatter: n.name,
                fontSize: 11,
                fontWeight: 600,
                color: '#3f3f46',
                backgroundColor: 'rgba(255,255,255,0.7)',
                padding: [1, 4],
                borderRadius: 3,
            },
            emphasis: {
                scale: 1.35,
                itemStyle: {
                    shadowBlur: 28,
                    shadowColor: withAlpha(baseColor, 0.7),
                    borderColor: '#fff',
                    borderWidth: 3,
                },
                label: { fontSize: 13 },
            },
            tooltip: {
                formatter: () => richTooltip({
                    title: n.name,
                    subtitle: n.file_path,
                    accent: baseColor,
                    rows: [
                        { label: '代码行数', value: n.loc, color: BRAND },
                        { label: '入度（被引）', value: n.fan_in, color: LAYER_PALETTE[1]!.from },
                        { label: '出度（依赖）', value: n.fan_out, color: LAYER_PALETTE[2]!.from },
                    ],
                    footer: n.in_cycle ? '⚠ 此节点处于循环依赖中' : undefined,
                }),
            },
        };
    });

    const links = data.links.map(l => ({
        source: l.source,
        target: l.target,
        value: l.value,
        lineStyle: {
            width: Math.min(4, 1 + Math.log2(l.value + 1)),
            opacity: 0.55,
            curveness: 0.14,
        },
    }));

    chart.setOption({
        ...chartBaseOption(),
        animationDuration: 1400,
        animationEasingUpdate: 'cubicInOut',
        backgroundColor: 'transparent',
        legend: [{
            ...legendStyle(),
            data: categories.map(c => c.name),
            bottom: 6,
        }],
        toolbox: toolboxBase({
            feature: {
                saveAsImage: { title: '保存图片', pixelRatio: 2 },
                restore: { title: '还原' },
                dataView: {
                    title: '数据视图', readOnly: true, lang: ['依赖数据', '关闭', '刷新'],
                    backgroundColor: 'rgba(255,255,255,0.98)', textColor: INK_MUTED,
                },
            },
        }),
        tooltip: { ...(chartBaseOption().tooltip as Record<string, unknown>), trigger: 'item' },
        series: [
            {
                type: 'graph',
                layout: 'force',
                roam: true,
                draggable: true,
                data: nodes,
                links,
                categories,
                force: {
                    repulsion: Math.max(80, 700 / Math.sqrt(nodes.length || 1)),
                    edgeLength: [50, 160],
                    gravity: 0.08,
                    friction: 0.6,
                },
                edgeSymbol: ['none', 'arrow'],
                edgeSymbolSize: 8,
                lineStyle: { color: 'source', opacity: 0.5, curveness: 0.14 },
                emphasis: {
                    focus: 'adjacency',
                    blurScope: 'coordinateSystem',
                    lineStyle: { width: 3, opacity: 0.95, color: SEVERITY.high.from },
                    label: { show: true },
                },
                blur: { itemStyle: { opacity: 0.16 }, lineStyle: { opacity: 0.05 } },
                animationDelay: (idx: number) => Math.min(idx * 12, 600),
                zoom: 1,
            },
        ],
    }, true);

    chart.off('click');
    chart.on('click', (params: any) => {
        if (params.dataType === 'node') showNodeDetail(container, data, params.data.id);
    });
}

function renderCycles(container: HTMLElement, cycles: DepCycle[]): void {
    const count = container.querySelector('#cycle-count') as HTMLElement;
    const list = container.querySelector('#cycle-list') as HTMLElement;

    count.innerHTML = cycles.length
        ? `发现 <strong style="color:#ef4444">${cycles.length}</strong> 处循环`
        : '未发现循环依赖';

    if (!cycles.length) {
        list.innerHTML = `<div class="empty-sm trend-up">✓ 架构无环，解耦良好</div>`;
        return;
    }

    list.innerHTML = cycles.slice(0, 10).map(c => {
        const color = SEVERITY_HEX[c.severity] || '#a1a1aa';
        return `
            <div class="cycle-item" style="border-left-color:${color}">
                <div class="cycle-head">
                    <span class="pill" style="background:${withAlpha(color, 0.14)};color:${color}">${c.severity.toUpperCase()}</span>
                    <span class="cycle-size">${c.size} 模块</span>
                </div>
                <div class="cycle-desc">${escapeHtml(c.description)}</div>
                ${c.shortest_cycle.length > 1 ? `
                    <div class="cycle-path">
                        ${c.shortest_cycle.map(m => `<code>${escapeHtml(shortModule(m))}</code>`).join(' <span class="cycle-arrow">→</span> ')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function renderStats(container: HTMLElement, data: DepGraphPayload): void {
    const el = container.querySelector('#graph-stats') as HTMLElement;
    const s = data.stats || {};
    const rows: [string, string | number][] = [
        ['节点总数', data.nodes.length],
        ['依赖边数', data.links.length],
        ['顶层类目', data.categories.length],
        ['循环依赖数', data.cycles.length],
        ['平均出度', s.avg_fan_out != null ? Number(s.avg_fan_out).toFixed(2) : '—'],
        ['平均入度', s.avg_fan_in != null ? Number(s.avg_fan_in).toFixed(2) : '—'],
    ];
    el.innerHTML = rows.map(([k, v]) => `
        <div class="stat-row"><span class="stat-label">${k}</span><span class="stat-value">${v}</span></div>
    `).join('');
}

function showNodeDetail(container: HTMLElement, data: DepGraphPayload, nodeId: string): void {
    const node = data.nodes.find(n => n.id === nodeId);
    if (!node) return;
    const outs = data.links.filter(l => l.source === nodeId).map(l => l.target);
    const ins = data.links.filter(l => l.target === nodeId).map(l => l.source);
    const el = container.querySelector('#node-detail') as HTMLElement;

    const fmtList = (arr: string[]) => arr.length
        ? `<ul class="dep-list">${arr.slice(0, 15).map(m => `<li><code>${escapeHtml(shortModule(m))}</code></li>`).join('')}${arr.length > 15 ? `<li class="more">+${arr.length - 15} more</li>` : ''}</ul>`
        : `<div class="empty-sm">—</div>`;

    el.innerHTML = `
        <div class="node-title">${escapeHtml(node.name)}</div>
        <div class="node-sub">${escapeHtml(node.file_path)}</div>
        <div class="node-stats">
            <div class="stat-chip"><b>${node.loc}</b><span>LOC</span></div>
            <div class="stat-chip"><b>${node.fan_out}</b><span>依赖</span></div>
            <div class="stat-chip"><b>${node.fan_in}</b><span>被引</span></div>
        </div>
        ${node.in_cycle ? '<div class="node-warn">⚠ 处于循环依赖中</div>' : ''}
        <div class="node-section-title">依赖的模块</div>
        ${fmtList(outs)}
        <div class="node-section-title">被哪些模块依赖</div>
        ${fmtList(ins)}
    `;
}

function shortModule(m: string): string {
    const parts = m.split('/');
    return parts.length <= 2 ? m : `.../${parts.slice(-2).join('/')}`;
}

function escapeHtml(s: string): string {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
}

