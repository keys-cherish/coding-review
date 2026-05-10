/**
 * 旭日图（ECharts sunburst）取代传统火焰图。
 * 目录 → 文件 → 函数 的层级，按 LOC 大小 + 复杂度着色。
 * 中心展示项目总规模。
 */
import * as echarts from 'echarts';

import { visApi, type HierarchyNode } from '../api';
import { pageShell } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';
import {
    BRAND, BRAND_DEEP, INK_MUTED, INK_SUBTLE,
    pickLayer, linearGradient, radialGradient,
    chartBaseOption, toolboxBase, richTooltip, withAlpha,
} from '../utils/chartTheme';

export async function renderFlame(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '代码火焰图',
        subtitle: '目录 → 文件 → 函数 的体积分布（ECharts 旭日图视角）',
        body: `
            <div class="viz-toolbar" id="flame-toolbar"></div>
            <div class="card chart-glass" style="margin-top:16px">
                <div class="chart-aurora aurora-flame"></div>
                <div class="card-header">
                    <div>
                        <div class="card-title">代码体积分布</div>
                        <div class="card-subtitle">点击节点下钻，右键回上级；外环 = 函数，环大小 = LOC</div>
                    </div>
                </div>
                <div class="card-body" style="padding:0;position:relative">
                    <div id="flame-chart" style="height:740px;position:relative;z-index:1"></div>
                </div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#flame-toolbar') as HTMLElement;
    const chartEl = container.querySelector('#flame-chart') as HTMLElement;
    const chart = echarts.init(chartEl);
    window.addEventListener('resize', () => chart.resize());

    await mountScanPicker(toolbar, async (scanId) => {
        chart.showLoading({ text: '构建层级...', maskColor: 'rgba(255,255,255,0.6)', textColor: BRAND });
        const { data, error } = await visApi.flame(scanId);
        chart.hideLoading();
        if (error || !data) {
            toast.error(error || '火焰图加载失败');
            return;
        }
        renderSunburst(chart, data);
    });
}

/**
 * 递归给每个节点附上渐变色：第 1 层用 LAYER_PALETTE 饱和色，
 * 向内逐层降饱和度并加亮，形成「外深内浅」的视觉层次
 */
function colorize(node: HierarchyNode, depth: number, rootIdx: number): void {
    const palette = pickLayer(rootIdx);
    const lighten = Math.min(0.55, depth * 0.13);

    (node as any).itemStyle = {
        color: linearGradient(
            blendWithWhite(palette.from, lighten),
            blendWithWhite(palette.to, lighten + 0.1),
            'd',
        ),
        borderWidth: Math.max(0.5, 2 - depth * 0.4),
        borderColor: 'rgba(255,255,255,0.85)',
        shadowBlur: depth === 0 ? 14 : 0,
        shadowColor: withAlpha(palette.from, 0.35),
    };
    if (node.children) {
        for (const c of node.children) colorize(c, depth + 1, rootIdx);
    }
}

function totalLoc(node: HierarchyNode): number {
    if (node.children?.length) {
        return node.children.reduce((sum, c) => sum + totalLoc(c), 0);
    }
    return node.value ?? 0;
}

function totalFiles(node: HierarchyNode, depth: number = 0): number {
    if (!node.children?.length) return depth >= 1 ? 1 : 0;
    return node.children.reduce((sum, c) => sum + totalFiles(c, depth + 1), 0);
}

function renderSunburst(chart: echarts.ECharts, data: HierarchyNode): void {
    const root = JSON.parse(JSON.stringify(data));
    if (root.children) {
        root.children.forEach((c: HierarchyNode, i: number) => colorize(c, 0, i));
    }

    const totalLOC = totalLoc(data);
    const fileCount = totalFiles(data);

    chart.setOption({
        ...chartBaseOption(),
        backgroundColor: 'transparent',
        animationDuration: 1500,
        animationEasing: 'elasticOut',
        animationDurationUpdate: 800,
        tooltip: {
            ...(chartBaseOption().tooltip as Record<string, unknown>),
            trigger: 'item',
            formatter: (p: any) => {
                const v = p.value || p.data.value || 0;
                const cv = p.data?.colorValue ?? p.data?.cyclomatic;
                const path = buildAncestorPath(p);
                const pct = totalLOC > 0 ? (v / totalLOC) * 100 : 0;
                const accent = (typeof p.color === 'string') ? p.color : BRAND;
                return richTooltip({
                    title: p.name || '(根)',
                    subtitle: path,
                    accent,
                    rows: [
                        { label: 'LOC', value: v, color: BRAND, bar: Math.min(100, pct), barColor: BRAND },
                        { label: '占总量', value: `${pct.toFixed(1)}%`, color: BRAND_DEEP },
                        ...(cv != null ? [{ label: '复杂度', value: cv, color: '#f59e0b' }] : []),
                    ],
                });
            },
        },
        toolbox: toolboxBase(),
        graphic: [
            {
                type: 'group',
                left: 'center',
                top: 'middle',
                z: 100,
                children: [
                    {
                        type: 'circle',
                        shape: { cx: 0, cy: 0, r: 50 },
                        style: {
                            fill: radialGradient('rgba(255,255,255,0.95)', 'rgba(252,242,238,0.65)'),
                            shadowBlur: 24,
                            shadowColor: 'rgba(207,124,101,0.30)',
                        },
                    },
                    {
                        type: 'text',
                        left: 'center',
                        top: -24,
                        style: {
                            text: '总规模',
                            fontSize: 10,
                            fontWeight: 600,
                            fill: INK_SUBTLE,
                            textAlign: 'center',
                            letterSpacing: 1.5,
                        },
                    },
                    {
                        type: 'text',
                        left: 'center',
                        top: -12,
                        style: {
                            text: formatNumber(totalLOC),
                            fontSize: 22,
                            fontWeight: 800,
                            fill: BRAND,
                            textAlign: 'center',
                            fontFamily: 'Inter, sans-serif',
                        },
                    },
                    {
                        type: 'text',
                        left: 'center',
                        top: 14,
                        style: {
                            text: 'LOC',
                            fontSize: 10,
                            fontWeight: 600,
                            fill: INK_MUTED,
                            textAlign: 'center',
                            letterSpacing: 2,
                        },
                    },
                    {
                        type: 'text',
                        left: 'center',
                        top: 30,
                        style: {
                            text: `${fileCount} 文件`,
                            fontSize: 10,
                            fontWeight: 500,
                            fill: INK_SUBTLE,
                            textAlign: 'center',
                        },
                    },
                ],
            },
        ],
        series: [{
            type: 'sunburst',
            data: root.children || [],
            radius: ['18%', '95%'],
            center: ['50%', '50%'],
            sort: (a: any, b: any) => (b.value || 0) - (a.value || 0),
            emphasis: {
                focus: 'ancestor',
                blurScope: 'global',
                itemStyle: {
                    shadowBlur: 18,
                    shadowColor: 'rgba(207,124,101,0.6)',
                    borderColor: '#fff',
                    borderWidth: 2,
                },
            },
            blur: { itemStyle: { opacity: 0.32 } },
            label: {
                rotate: 'radial',
                color: '#fff',
                fontSize: 11,
                fontWeight: 600,
                textBorderColor: 'rgba(0,0,0,0.4)',
                textBorderWidth: 1,
                minAngle: 4,
            },
            levels: [
                {},
                {
                    r0: '18%', r: '36%',
                    itemStyle: { borderWidth: 2, borderColor: 'rgba(255,255,255,0.95)' },
                    label: { rotate: 'tangential', fontSize: 12.5, fontWeight: 700 },
                },
                {
                    r0: '36%', r: '58%',
                    itemStyle: { borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.9)' },
                    label: { align: 'right', fontSize: 11, fontWeight: 600 },
                },
                {
                    r0: '58%', r: '78%',
                    itemStyle: { borderWidth: 1, borderColor: 'rgba(255,255,255,0.85)' },
                    label: { align: 'right', fontSize: 10, fontWeight: 500 },
                },
                {
                    r0: '78%', r: '95%',
                    itemStyle: { borderWidth: 0.5, borderColor: 'rgba(255,255,255,0.75)' },
                    label: {
                        position: 'outside', fontSize: 9.5, fontWeight: 500,
                        color: INK_MUTED, textBorderColor: 'transparent', textBorderWidth: 0,
                    },
                },
            ],
            animationDelay: (idx: number) => idx * 22,
        }],
    }, true);
}

/**
 * 把 #rrggbb 与白色混合：amount 0~1 表示掺入白色比例
 */
function blendWithWhite(hex: string, amount: number): string {
    const c = hex.replace('#', '');
    const full = c.length === 3 ? c.split('').map(ch => ch + ch).join('') : c;
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    const mix = (v: number) => Math.round(v + (255 - v) * amount);
    return `rgb(${mix(r)}, ${mix(g)}, ${mix(b)})`;
}

function buildAncestorPath(p: any): string {
    if (!p.treePathInfo) return p.name || '';
    return p.treePathInfo.map((t: any) => t.name).filter(Boolean).join(' / ');
}

function formatNumber(n: number): string {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k';
    return String(n);
}
