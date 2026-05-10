/**
 * 六维架构雷达 + 架构模式识别合并视图。
 *
 * 左：ECharts 雷达图，当前 vs 上一次扫描
 * 右：维度解读 + 架构模式识别卡片
 */
import * as echarts from 'echarts';

import { visApi, type RadarPayload, type ArchPayload } from '../api';
import { pageShell, emptyState } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';
import {
    BRAND, BRAND_DEEP, BRAND_GLOW, INK_MUTED, INK_SUBTLE,
    BRAND_GRADIENT, chartBaseOption, legendStyle, toolboxBase,
    richTooltip, scoreColor, withAlpha,
} from '../utils/chartTheme';

const DIM_ICONS = ['◆', '▣', '◈', '⬢', '◉', '✦'];

export async function renderRadar(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '六维架构雷达',
        subtitle: '架构清晰度 · 分层隔离度 · 模块解耦度 · 组件内聚度 · 规范执行力 · 重复冗余度',
        body: `
            <div class="viz-toolbar" id="radar-toolbar"></div>

            <div class="split-2" style="margin-top:16px">
                <div class="card chart-glass">
                    <div class="chart-aurora aurora-radar"></div>
                    <div class="card-header">
                        <div>
                            <div class="card-title">六维健康度</div>
                            <div class="card-subtitle" id="radar-grade"></div>
                        </div>
                    </div>
                    <div class="card-body" style="position:relative">
                        <div id="radar6" style="height:480px;position:relative;z-index:1"></div>
                    </div>
                </div>

                <div class="stack-v">
                    <div class="card">
                        <div class="card-header">
                            <div class="card-title">架构模式识别</div>
                            <div class="card-subtitle" id="arch-primary">—</div>
                        </div>
                        <div class="card-body" id="arch-body">
                            <div class="empty"><div class="empty-title">分析中...</div></div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-header"><div class="card-title">维度解读</div></div>
                        <div class="card-body" id="radar-detail"></div>
                    </div>
                </div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#radar-toolbar') as HTMLElement;
    const chartEl = container.querySelector('#radar6') as HTMLElement;
    const chart = echarts.init(chartEl);
    window.addEventListener('resize', () => chart.resize());

    await mountScanPicker(toolbar, async (scanId) => {
        chart.showLoading({ text: '加载中...', maskColor: 'rgba(255,255,255,0.6)', textColor: BRAND });
        const [radarRes, archRes] = await Promise.all([
            visApi.radar(scanId),
            visApi.architecture(scanId),
        ]);
        chart.hideLoading();

        if (radarRes.error || !radarRes.data) {
            toast.error(radarRes.error || '雷达数据加载失败');
            return;
        }
        renderRadarChart(chart, radarRes.data);
        renderGrade(container, radarRes.data);
        renderDimensionDetail(container, radarRes.data);

        if (archRes.data) renderArchitecture(container, archRes.data);
    });
}

function renderRadarChart(chart: echarts.ECharts, data: RadarPayload): void {
    const indicators = data.dimensions.map((d, i) => ({
        name: `${DIM_ICONS[i % DIM_ICONS.length]}  ${d.name}`,
        max: 100,
    }));
    const currentVals = data.dimensions.map(d => d.score);
    const prevVals = data.previous?.dimensions?.map(d => d.score);

    const seriesData: any[] = [{
        value: currentVals,
        name: '当前版本',
        symbol: 'circle',
        symbolSize: 9,
        areaStyle: { color: BRAND_GRADIENT.soft() },
        lineStyle: {
            width: 3,
            color: BRAND,
            shadowBlur: 14,
            shadowColor: BRAND_GLOW,
        },
        itemStyle: {
            color: BRAND,
            borderColor: '#fff',
            borderWidth: 2.5,
            shadowBlur: 10,
            shadowColor: BRAND_GLOW,
        },
        label: {
            show: true,
            formatter: (p: any) => Number(p.value).toFixed(0),
            color: BRAND_DEEP,
            fontSize: 11,
            fontWeight: 700,
            backgroundColor: 'rgba(255,255,255,0.85)',
            padding: [2, 5],
            borderRadius: 4,
            shadowBlur: 4,
            shadowColor: 'rgba(0,0,0,0.06)',
        },
    }];
    if (prevVals) {
        seriesData.push({
            value: prevVals,
            name: '上一次扫描',
            symbol: 'circle',
            symbolSize: 5,
            lineStyle: {
                color: '#a1a1aa',
                width: 1.5,
                type: 'dashed',
                opacity: 0.7,
            },
            itemStyle: { color: '#a1a1aa', borderColor: '#fff', borderWidth: 1 },
            areaStyle: { color: 'rgba(161,161,170,0.05)' },
        });
    }

    const overallText = data.overall.toFixed(1);
    const gradeColor = gradeToHex(data.grade);

    chart.setOption({
        ...chartBaseOption(),
        animationDuration: 1500,
        animationEasing: 'elasticOut',
        animationDelay: (idx: number) => idx * 80,
        backgroundColor: 'transparent',
        legend: {
            ...legendStyle(),
            bottom: 4,
        },
        toolbox: toolboxBase(),
        tooltip: {
            ...(chartBaseOption().tooltip as Record<string, unknown>),
            trigger: 'item',
            formatter: (p: any) => {
                const isCurrent = p.seriesIndex === 0 || p.name === '当前版本';
                const dims = data.dimensions;
                const prev = data.previous?.dimensions;
                const rows = dims.map((d, i) => {
                    const cur = d.score;
                    const old = prev?.[i]?.score;
                    return {
                        label: d.name,
                        value: cur.toFixed(1),
                        color: scoreColor(cur),
                        bar: cur,
                        barColor: scoreColor(cur),
                        ...(old != null && { footer: `上次 ${old.toFixed(1)}` }),
                    };
                });
                return richTooltip({
                    title: isCurrent ? '当前版本' : '上一次扫描',
                    subtitle: `综合 ${overallText} · 等级 ${data.grade}`,
                    rows,
                    accent: isCurrent ? BRAND : '#a1a1aa',
                });
            },
        },
        radar: {
            indicator: indicators,
            shape: 'polygon',
            center: ['50%', '52%'],
            radius: '68%',
            axisName: {
                color: INK_MUTED,
                fontSize: 12.5,
                fontWeight: 600,
                padding: [4, 6],
            },
            splitLine: {
                lineStyle: {
                    color: ['#f4e4dc', '#e9d2c8', '#dec0b3', '#d3ae9f', '#c89c8a'],
                    width: 1.2,
                },
            },
            splitArea: {
                areaStyle: {
                    color: [
                        'rgba(255,255,255,0.0)',
                        'rgba(207,124,101,0.04)',
                        'rgba(207,124,101,0.08)',
                        'rgba(207,124,101,0.12)',
                        'rgba(207,124,101,0.18)',
                    ],
                    shadowBlur: 8,
                    shadowColor: BRAND_GLOW,
                },
            },
            axisLine: { lineStyle: { color: 'rgba(207,124,101,0.35)', width: 1 } },
        },
        graphic: [
            {
                type: 'group',
                left: 'center',
                top: 'middle',
                z: 0,
                children: [
                    {
                        type: 'circle',
                        shape: { cx: 0, cy: 0, r: 36 },
                        style: {
                            fill: withAlpha(gradeColor, 0.10),
                            shadowBlur: 24,
                            shadowColor: withAlpha(gradeColor, 0.35),
                        },
                    },
                    {
                        type: 'text',
                        left: 'center',
                        top: -16,
                        style: {
                            text: overallText,
                            fontSize: 26,
                            fontWeight: 800,
                            fill: gradeColor,
                            textAlign: 'center',
                            fontFamily: 'Inter, sans-serif',
                        },
                    },
                    {
                        type: 'text',
                        left: 'center',
                        top: 14,
                        style: {
                            text: `等级 ${data.grade}`,
                            fontSize: 11,
                            fontWeight: 600,
                            fill: INK_SUBTLE,
                            textAlign: 'center',
                            letterSpacing: 1,
                        },
                    },
                ],
            },
        ],
        series: [{
            type: 'radar',
            data: seriesData,
            emphasis: {
                focus: 'series',
                lineStyle: { width: 4 },
                areaStyle: { color: BRAND_GRADIENT.soft() },
            },
        }],
    }, true);
}

function renderGrade(container: HTMLElement, data: RadarPayload): void {
    const grade = container.querySelector('#radar-grade')!;
    const prev = data.previous?.overall;
    const delta = prev != null ? (data.overall - prev).toFixed(1) : null;
    const arrow = delta && Number(delta) > 0 ? '↑' : delta && Number(delta) < 0 ? '↓' : '→';
    const deltaCls = delta && Number(delta) > 0 ? 'trend-up' : delta && Number(delta) < 0 ? 'trend-down' : '';
    grade.innerHTML = `
        综合评分 <strong style="color:${BRAND};font-size:18px">${data.overall.toFixed(1)}</strong>
        · 等级 <span class="pill pill-${gradeColor(data.grade)}">${data.grade}</span>
        ${delta ? `<span class="${deltaCls}" style="margin-left:8px;font-weight:600">${arrow} ${Math.abs(Number(delta)).toFixed(1)}</span>` : ''}
    `;
}

function renderDimensionDetail(container: HTMLElement, data: RadarPayload): void {
    const el = container.querySelector('#radar-detail')!;
    const prev = data.previous?.dimensions;
    const rows = data.dimensions.map((d, i) => {
        const p = prev?.[i]?.score;
        const delta = p != null ? d.score - p : null;
        const arrow = delta == null ? '' : delta > 0.5 ? '↑' : delta < -0.5 ? '↓' : '→';
        const cls = delta == null ? '' : delta > 0.5 ? 'trend-up' : delta < -0.5 ? 'trend-down' : '';
        const barColor = scoreColor(d.score);
        const icon = DIM_ICONS[i % DIM_ICONS.length];
        return `
            <div class="dim-row">
                <div class="dim-row-head">
                    <span class="dim-name"><span class="dim-icon" style="color:${barColor}">${icon}</span> ${escapeHtml(d.name)}</span>
                    <span class="dim-score">${d.score.toFixed(1)} <span class="${cls}" style="font-size:11px;margin-left:4px">${arrow}</span></span>
                </div>
                <div class="dim-bar">
                    <span style="width:${d.score}%;background:linear-gradient(90deg, ${barColor}, ${withAlpha(barColor, 0.6)});box-shadow:0 0 10px ${withAlpha(barColor, 0.5)}"></span>
                </div>
                <div class="dim-detail">${escapeHtml(d.detail)}</div>
            </div>
        `;
    }).join('');
    el.innerHTML = rows;
}

function renderArchitecture(container: HTMLElement, data: ArchPayload): void {
    const primary = container.querySelector('#arch-primary') as HTMLElement;
    primary.innerHTML = `主模式: <strong style="color:${BRAND}">${escapeHtml(data.primary || '未识别')}</strong>`;

    const body = container.querySelector('#arch-body')!;
    if (!data.detected.length) {
        body.innerHTML = emptyState({ title: '未识别出明显架构模式', desc: '项目可能是单体或目录结构扁平' });
        return;
    }

    const patterns = data.detected.slice(0, 6).map(p => {
        const pct = Math.round(p.confidence * 100);
        return `
            <div class="arch-item">
                <div class="arch-item-head">
                    <span class="arch-pattern">${escapeHtml(p.pattern)}</span>
                    <span class="arch-conf">${pct}%</span>
                </div>
                <div class="arch-bar"><span style="width:${pct}%"></span></div>
                <div class="arch-reason">${escapeHtml(p.reason)}</div>
                ${p.evidence.length ? `<div class="arch-evidence">${p.evidence.map(e => `<code>${escapeHtml(e)}</code>`).join('')}</div>` : ''}
            </div>
        `;
    }).join('');

    const layers = data.layers.length ? `
        <div class="arch-layers">
            <div class="arch-layers-title">识别到的分层</div>
            <div class="arch-layer-grid">
                ${data.layers.map(l => `
                    <div class="arch-layer-chip">
                        <div class="arch-layer-name">${escapeHtml(l.name)}</div>
                        <div class="arch-layer-count">${l.files_count} 文件</div>
                        <div class="arch-layer-dirs">${l.dirs.slice(0, 3).map(d => `<code>${escapeHtml(d)}</code>`).join(' ')}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    ` : '';

    const lv = data.layer_violations;
    const violations = (lv && lv.summary.violation_count > 0) ? `
        <div class="arch-layers" style="margin-top: var(--sp-4)">
            <div class="arch-layers-title">
                分层违规
                <span class="pill pill-danger">${lv.summary.violation_count}</span>
                <span class="pill pill-muted">违规率 ${(lv.summary.violation_ratio * 100).toFixed(1)}%</span>
            </div>
            <div class="violation-list">
                ${lv.violations.slice(0, 20).map(v => `
                    <div class="violation-row sev-${escapeHtml(v.severity)}">
                        <span class="pill pill-${v.severity === 'error' ? 'danger' : 'warn'}">${escapeHtml(v.severity)}</span>
                        <code class="violation-src">${escapeHtml(v.src_file)}</code>
                        <span class="violation-arrow">→</span>
                        <code class="violation-dst">${escapeHtml(v.dst_file)}</code>
                        <div class="violation-reason">
                            <span class="layer-tag">${escapeHtml(v.src_layer)}</span>
                            →
                            <span class="layer-tag">${escapeHtml(v.dst_layer)}</span>
                            <span>${escapeHtml(v.reason)}</span>
                        </div>
                    </div>
                `).join('')}
                ${lv.violations.length > 20 ? `<div class="violation-more">还有 ${lv.violations.length - 20} 条未显示</div>` : ''}
            </div>
        </div>
    ` : (lv ? `
        <div class="arch-layers" style="margin-top: var(--sp-4)">
            <div class="arch-layers-title">分层违规 <span class="pill pill-ok">0</span></div>
            <div class="arch-reason">未发现分层约束违规（共分析 ${lv.summary.classified_edges} 条跨层边）</div>
        </div>
    ` : '');

    body.innerHTML = `
        <div class="arch-list">${patterns}</div>
        ${layers}
        ${violations}
        <div class="arch-meta">
            <span>跨层依赖比 <strong>${(data.cross_layer_ratio * 100).toFixed(1)}%</strong></span>
            <span>顶层目录 ${data.top_dirs.slice(0, 4).map(d => `<code>${escapeHtml(d)}</code>`).join(' ')}</span>
        </div>
    `;
}

function gradeColor(g: string): string {
    if (g === 'A') return 'ok';
    if (g === 'B') return 'info';
    if (g === 'C') return 'warn';
    return 'danger';
}

function gradeToHex(g: string): string {
    if (g === 'A') return '#10b981';
    if (g === 'B') return '#3b82f6';
    if (g === 'C') return '#f59e0b';
    return '#ef4444';
}

function escapeHtml(s: string): string {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
}
