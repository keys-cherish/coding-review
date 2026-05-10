/**
 * 图表统一主题：渐变、阴影、富 tooltip、调色板
 *
 * 所有可视化视图（Radar/Graph/Treemap/Flame）共用这里的色彩系统与样式工具
 * 以保证「一眼看上去就是同一个产品」的视觉一致性。
 */
import * as echarts from 'echarts';

// ============ 品牌色与基础色 ============

export const BRAND = '#cf7c65';
export const BRAND_DEEP = '#b86954';
export const BRAND_LIGHT = '#f1b7a5';
export const BRAND_GLOW = 'rgba(207, 124, 101, 0.45)';

export const INK = '#27272a';
export const INK_MUTED = '#52525b';
export const INK_SUBTLE = '#71717a';
export const PAGE_BG_SOFT = 'rgba(250, 250, 252, 0.6)';

// ============ 严重度色板（含渐变） ============

export interface GradientPair { from: string; to: string; glow: string; }

export const SEVERITY: Record<'critical' | 'high' | 'medium' | 'low' | 'ok', GradientPair> = {
    critical: { from: '#dc2626', to: '#fb7185', glow: 'rgba(220, 38, 38, 0.45)' },
    high:     { from: '#ef4444', to: '#fca5a5', glow: 'rgba(239, 68, 68, 0.40)' },
    medium:   { from: '#f59e0b', to: '#fcd34d', glow: 'rgba(245, 158, 11, 0.40)' },
    low:      { from: '#6366f1', to: '#a5b4fc', glow: 'rgba(99, 102, 241, 0.30)' },
    ok:       { from: '#10b981', to: '#6ee7b7', glow: 'rgba(16, 185, 129, 0.35)' },
};

// ============ 多色调色板（带渐变） ============

export const LAYER_PALETTE: GradientPair[] = [
    { from: '#cf7c65', to: '#f1b7a5', glow: 'rgba(207, 124, 101, 0.40)' },
    { from: '#6366f1', to: '#a5b4fc', glow: 'rgba(99, 102, 241, 0.40)' },
    { from: '#10b981', to: '#6ee7b7', glow: 'rgba(16, 185, 129, 0.40)' },
    { from: '#f59e0b', to: '#fcd34d', glow: 'rgba(245, 158, 11, 0.40)' },
    { from: '#8b5cf6', to: '#c4b5fd', glow: 'rgba(139, 92, 246, 0.40)' },
    { from: '#3b82f6', to: '#93c5fd', glow: 'rgba(59, 130, 246, 0.40)' },
    { from: '#ec4899', to: '#f9a8d4', glow: 'rgba(236, 72, 153, 0.40)' },
    { from: '#14b8a6', to: '#5eead4', glow: 'rgba(20, 184, 166, 0.40)' },
    { from: '#f97316', to: '#fdba74', glow: 'rgba(249, 115, 22, 0.40)' },
    { from: '#a855f7', to: '#d8b4fe', glow: 'rgba(168, 85, 247, 0.40)' },
];

// ============ ECharts LinearGradient 工厂 ============

/**
 * 构造一个 ECharts 线性渐变（默认从上到下）
 * direction: 'v' = 上到下, 'h' = 左到右, 'd' = 对角线
 */
export function linearGradient(
    from: string,
    to: string,
    direction: 'v' | 'h' | 'd' = 'v',
): echarts.graphic.LinearGradient {
    const coords =
        direction === 'h' ? [0, 0, 1, 0] :
        direction === 'd' ? [0, 0, 1, 1] :
        [0, 0, 0, 1];
    return new echarts.graphic.LinearGradient(coords[0], coords[1], coords[2], coords[3], [
        { offset: 0, color: from },
        { offset: 1, color: to },
    ]);
}

/** 径向渐变：中心亮、边缘暗，常用于发光球 */
export function radialGradient(
    center: string,
    edge: string,
): echarts.graphic.RadialGradient {
    return new echarts.graphic.RadialGradient(0.5, 0.5, 0.6, [
        { offset: 0, color: center },
        { offset: 1, color: edge },
    ]);
}

// ============ 品牌渐变快捷常量 ============

export const BRAND_GRADIENT = {
    /** 实心填充用：从深到浅纵向渐变 */
    fill: () => linearGradient(BRAND, BRAND_LIGHT, 'v'),
    /** 半透明填充用：雷达 areaStyle */
    soft: () => linearGradient('rgba(207,124,101,0.45)', 'rgba(207,124,101,0.05)', 'v'),
    /** 横向渐变：进度条等 */
    horizontal: () => linearGradient(BRAND, BRAND_LIGHT, 'h'),
};

/** 严重度对应的渐变填充（用于 ECharts itemStyle.color） */
export function severityGradient(level: keyof typeof SEVERITY): echarts.graphic.LinearGradient {
    const p = SEVERITY[level];
    return linearGradient(p.from, p.to, 'v');
}

// ============ 玻璃质感 itemStyle ============

/**
 * 返回带 shadowBlur 的 itemStyle —— 用于关键节点 / 警告项
 */
export function glowItemStyle(color: string, blur: number = 18): Record<string, unknown> {
    return {
        color,
        shadowBlur: blur,
        shadowColor: color,
        borderColor: 'rgba(255,255,255,0.85)',
        borderWidth: 2,
    };
}

// ============ 富 HTML tooltip ============

export interface TooltipRow {
    label: string;
    value: string | number;
    color?: string;
    /** 0-100 的迷你进度条 */
    bar?: number;
    barColor?: string;
}

/**
 * 统一的富 tooltip 渲染：标题 + 副标题 + 多行数据 + 可选迷你进度条
 */
export function richTooltip(opts: {
    title: string;
    subtitle?: string;
    rows: TooltipRow[];
    accent?: string;
    footer?: string;
}): string {
    const accent = opts.accent ?? BRAND;
    const head = `
        <div style="font-weight:700;font-size:13px;color:${INK};letter-spacing:0.01em;line-height:1.3">
            ${escape(opts.title)}
        </div>
        ${opts.subtitle ? `<div style="font-size:11px;color:${INK_SUBTLE};margin-top:2px">${escape(opts.subtitle)}</div>` : ''}
        <div style="height:1px;background:linear-gradient(90deg,${accent}55,transparent);margin:6px 0"></div>
    `;

    const body = opts.rows.map(r => {
        const valColor = r.color ?? INK;
        const valHtml = `<span style="color:${valColor};font-weight:700;font-variant-numeric:tabular-nums">${escape(String(r.value))}</span>`;
        const barHtml = r.bar != null
            ? `<div style="height:3px;margin-top:3px;border-radius:999px;background:rgba(0,0,0,0.06);overflow:hidden">
                 <div style="height:100%;width:${Math.max(0, Math.min(100, r.bar))}%;background:${r.barColor ?? accent};border-radius:999px"></div>
               </div>` : '';
        return `
            <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;margin:3px 0">
                <span style="color:${INK_MUTED}">${escape(r.label)}</span>${valHtml}
            </div>${barHtml}
        `;
    }).join('');

    const footer = opts.footer
        ? `<div style="margin-top:6px;padding-top:6px;border-top:1px dashed rgba(0,0,0,0.08);font-size:11px;color:${INK_SUBTLE}">${opts.footer}</div>`
        : '';

    return `<div style="min-width:180px;padding:2px">${head}${body}${footer}</div>`;
}

function escape(s: string): string {
    return s.replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!
    ));
}

// ============ 图表统一基础项 ============

/**
 * 通用基础配置：tooltip 容器样式、文字、过渡动画
 * 子图把这个对象 spread 到 setOption 顶层
 */
export function chartBaseOption(): Record<string, unknown> {
    return {
        textStyle: {
            fontFamily: 'Inter, -apple-system, "Segoe UI", "PingFang SC", sans-serif',
            color: INK,
        },
        animationDuration: 1400,
        animationEasing: 'cubicOut',
        animationDurationUpdate: 800,
        animationEasingUpdate: 'cubicInOut',
        tooltip: {
            backgroundColor: 'rgba(255, 255, 255, 0.96)',
            borderColor: 'rgba(207, 124, 101, 0.25)',
            borderWidth: 1,
            padding: [10, 12],
            extraCssText: 'box-shadow: 0 12px 32px -6px rgba(40, 30, 25, 0.18), 0 4px 10px -2px rgba(40, 30, 25, 0.08); border-radius: 10px; backdrop-filter: blur(8px);',
            textStyle: { color: INK, fontSize: 12 },
        },
    };
}

/**
 * 通用图例样式：圆角矩形图标、加粗字、宽间距
 */
export function legendStyle(extra?: Record<string, unknown>): Record<string, unknown> {
    return {
        icon: 'roundRect',
        itemWidth: 14,
        itemHeight: 8,
        itemGap: 16,
        textStyle: {
            color: INK_MUTED,
            fontSize: 12,
            fontWeight: 600,
            padding: [0, 0, 0, 4],
        },
        ...extra,
    };
}

/**
 * 通用 toolbox：保存图片、还原
 */
export function toolboxBase(extra?: Record<string, unknown>): Record<string, unknown> {
    return {
        right: 12,
        top: 8,
        itemSize: 14,
        itemGap: 10,
        iconStyle: { borderColor: INK_SUBTLE },
        emphasis: { iconStyle: { borderColor: BRAND } },
        feature: {
            saveAsImage: { title: '保存图片', pixelRatio: 2 },
            restore: { title: '还原' },
        },
        ...extra,
    };
}

// ============ 取色辅助 ============

export function pickLayer(idx: number): GradientPair {
    return LAYER_PALETTE[idx % LAYER_PALETTE.length]!;
}

/**
 * 给颜色叠加 alpha：兼容 #rgb / #rrggbb / hsl(...) / rgb(...)
 */
export function withAlpha(color: string, alpha: number): string {
    if (color.startsWith('#')) {
        const c = color.slice(1);
        const full = c.length === 3 ? c.split('').map(ch => ch + ch).join('') : c;
        const r = parseInt(full.slice(0, 2), 16);
        const g = parseInt(full.slice(2, 4), 16);
        const b = parseInt(full.slice(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    if (color.startsWith('hsl(')) {
        return color.replace(/^hsl\(/i, 'hsla(').replace(/\)$/, `, ${alpha})`);
    }
    if (color.startsWith('rgb(')) {
        return color.replace(/^rgb\(/i, 'rgba(').replace(/\)$/, `, ${alpha})`);
    }
    return color;
}

/**
 * 把 0-100 的分数映射成「红→琥珀→翠绿」连续色
 * 高分=绿，低分=红
 */
export function scoreColor(score: number): string {
    const s = Math.max(0, Math.min(100, score));
    const hue = (s / 100) * 140;
    return `hsl(${hue}, 72%, 48%)`;
}
