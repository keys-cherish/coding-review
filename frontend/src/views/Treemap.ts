/**
 * 热力 Treemap：目录 → 文件 → 函数。
 * value = LOC，colorValue = 复杂度或问题数。
 * 配色采用 visualMap 连续渐变（绿→蓝→紫→橙→红）。
 */
import * as echarts from 'echarts';

import { visApi, type HierarchyNode } from '../api';
import { pageShell } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';
import {
    BRAND, INK_MUTED,
    chartBaseOption, toolboxBase, richTooltip, withAlpha,
} from '../utils/chartTheme';

/**
 * 热力色阶：从冷（健康）到暖（高风险）
 * 6 段分布在 visualMap.inRange.color 数组里，由 ECharts 自动插值
 */
const HEAT_COLORS = [
    '#10b981', // 健康-翠绿
    '#34d399', // 浅绿
    '#60a5fa', // 蓝
    '#a78bfa', // 紫
    '#f59e0b', // 琥珀
    '#ef4444', // 红
];

export async function renderTreemap(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '热力 Treemap',
        subtitle: '按 LOC 布局，颜色=复杂度/问题密度，点击下钻',
        body: `
            <div class="viz-toolbar" id="treemap-toolbar"></div>
            <div class="card chart-glass" style="margin-top:16px">
                <div class="chart-aurora aurora-treemap"></div>
                <div class="card-header">
                    <div>
                        <div class="card-title">模块热力</div>
                        <div class="card-subtitle" id="treemap-hint">深暖色 = 高复杂度 / 高问题密度；面积 = 代码行数</div>
                    </div>
                </div>
                <div class="card-body" style="padding:0;position:relative">
                    <div id="treemap-chart" style="height:720px;position:relative;z-index:1"></div>
                </div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#treemap-toolbar') as HTMLElement;
    const chartEl = container.querySelector('#treemap-chart') as HTMLElement;
    const chart = echarts.init(chartEl);
    window.addEventListener('resize', () => chart.resize());

    await mountScanPicker(toolbar, async (scanId) => {
        chart.showLoading({ text: '绘制热力...', maskColor: 'rgba(255,255,255,0.6)', textColor: BRAND });
        const { data, error } = await visApi.treemap(scanId);
        chart.hideLoading();
        if (error || !data) {
            toast.error(error || 'Treemap 加载失败');
            return;
        }
        renderTm(chart, data);
    });
}

function maxColorValue(node: HierarchyNode): number {
    let best = node.colorValue ?? node.cyclomatic ?? 0;
    if (node.children) for (const c of node.children) best = Math.max(best, maxColorValue(c));
    return best;
}

function renderTm(chart: echarts.ECharts, data: HierarchyNode): void {
    const maxC = Math.max(1, maxColorValue(data));
    chart.setOption({
        ...chartBaseOption(),
        backgroundColor: 'transparent',
        animationDuration: 1200,
        animationEasing: 'cubicOut',
        tooltip: {
            ...(chartBaseOption().tooltip as Record<string, unknown>),
            formatter: (info: any) => {
                const n = info.data;
                const cv = n.colorValue ?? n.cyclomatic ?? 0;
                const path = info.treePathInfo.map((t: any) => t.name).join(' / ');
                const cvPct = Math.round((cv / maxC) * 100);
                const heatColor = pickHeatColor(cvPct);
                return richTooltip({
                    title: n.name,
                    subtitle: path,
                    accent: heatColor,
                    rows: [
                        { label: '代码行数 (LOC)', value: n.value, color: BRAND, bar: Math.min(100, n.value / 50), barColor: BRAND },
                        { label: '复杂度 / 热度', value: cv, color: heatColor, bar: cvPct, barColor: heatColor },
                    ],
                    footer: cvPct >= 70 ? '⚠ 该模块复杂度偏高，建议优先重构' : undefined,
                });
            },
        },
        toolbox: toolboxBase({
            feature: {
                saveAsImage: { title: '保存图片', pixelRatio: 2 },
                restore: { title: '还原' },
            },
        }),
        visualMap: {
            type: 'continuous',
            min: 0,
            max: maxC,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: 6,
            itemWidth: 14,
            itemHeight: 180,
            text: ['高复杂度', '低复杂度'],
            textStyle: { color: INK_MUTED, fontSize: 11, fontWeight: 600 },
            inRange: { color: HEAT_COLORS },
            dimension: 'colorValue' as any,
        },
        series: [{
            type: 'treemap',
            roam: 'move',
            data: data.children || [],
            leafDepth: 3,
            visibleMin: 4,
            squareRatio: 0.62,
            upperLabel: {
                show: true,
                height: 24,
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                textBorderColor: 'rgba(0,0,0,0.45)',
                textBorderWidth: 1,
            },
            breadcrumb: {
                show: true,
                height: 28,
                bottom: 32,
                emptyItemWidth: 22,
                itemStyle: {
                    color: 'rgba(207,124,101,0.10)',
                    borderColor: 'rgba(207,124,101,0.22)',
                    borderWidth: 1,
                    textStyle: { color: INK_MUTED, fontSize: 11.5, fontWeight: 600 },
                    shadowBlur: 6,
                    shadowColor: 'rgba(207,124,101,0.18)',
                },
                emphasis: {
                    itemStyle: {
                        color: BRAND,
                        textStyle: { color: '#fff' },
                    },
                },
            },
            label: {
                show: true,
                formatter: (p: any) => {
                    const n = p.name || '';
                    return n.length > 18 ? n.slice(0, 16) + '…' : n;
                },
                fontSize: 11,
                fontWeight: 600,
                color: '#fff',
                textBorderColor: 'rgba(0,0,0,0.45)',
                textBorderWidth: 1.2,
            },
            itemStyle: {
                borderColor: 'rgba(255,255,255,0.85)',
                borderWidth: 1.5,
                gapWidth: 1.5,
                shadowBlur: 4,
                shadowColor: 'rgba(40,30,25,0.10)',
            },
            emphasis: {
                focus: 'descendant',
                itemStyle: {
                    borderColor: '#fff',
                    borderWidth: 3,
                    shadowBlur: 22,
                    shadowColor: withAlpha(BRAND, 0.55),
                },
                label: { fontSize: 13 },
            },
            blur: { itemStyle: { opacity: 0.55 } },
            levels: [
                {
                    itemStyle: {
                        borderColor: 'rgba(207,124,101,0.30)',
                        borderWidth: 3,
                        gapWidth: 3,
                    },
                    upperLabel: {
                        show: true, height: 26, fontSize: 13, fontWeight: 700,
                        color: '#fff', textBorderColor: 'rgba(0,0,0,0.5)', textBorderWidth: 1,
                    },
                },
                {
                    colorSaturation: [0.45, 0.85],
                    itemStyle: {
                        borderColor: 'rgba(255,255,255,0.85)',
                        borderWidth: 2,
                        gapWidth: 2,
                    },
                },
                {
                    colorSaturation: [0.55, 0.95],
                    itemStyle: {
                        borderColor: 'rgba(255,255,255,0.9)',
                        borderWidth: 1,
                        gapWidth: 1,
                    },
                },
            ],
            visualMin: 0,
            visualMax: maxC,
            visualDimension: 'colorValue',
            colorMappingBy: 'value',
            animationDuration: 1200,
            animationDurationUpdate: 800,
            animationEasing: 'cubicOut',
        }],
    }, true);
}

/**
 * 把 0-100 的百分比映射到 HEAT_COLORS 的某个色段
 */
function pickHeatColor(pct: number): string {
    const idx = Math.max(0, Math.min(HEAT_COLORS.length - 1, Math.floor((pct / 100) * HEAT_COLORS.length)));
    return HEAT_COLORS[idx]!;
}

