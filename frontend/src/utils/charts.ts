import * as echarts from 'echarts';

const brand = '#cf7c65';
const brandSoft = '#f7e2db';

export function initRadarChart(el: HTMLElement): echarts.ECharts {
    const chart = echarts.init(el);
    chart.setOption({
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, data: ['当前版本', '上一版本'], textStyle: { fontSize: 11 } },
        radar: {
            indicator: [
                { name: '架构清晰度', max: 100 },
                { name: '分层隔离度', max: 100 },
                { name: '模块解耦度', max: 100 },
                { name: '组件内聚度', max: 100 },
                { name: '规范执行力', max: 100 },
                { name: '重复冗余度', max: 100 },
            ],
            axisName: { color: '#52525b', fontSize: 11 },
            splitLine: { lineStyle: { color: '#e4e4e7' } },
            splitArea: { areaStyle: { color: ['rgba(250,250,250,0.5)', 'rgba(244,244,245,0.4)'] } },
        },
        series: [{
            type: 'radar',
            symbol: 'circle',
            symbolSize: 6,
            data: [
                {
                    value: [85, 72, 68, 78, 82, 70],
                    name: '当前版本',
                    areaStyle: { color: brandSoft },
                    lineStyle: { color: brand, width: 2 },
                    itemStyle: { color: brand },
                },
                {
                    value: [72, 60, 55, 65, 70, 58],
                    name: '上一版本',
                    lineStyle: { color: '#a1a1aa', width: 1.5, type: 'dashed' },
                    itemStyle: { color: '#a1a1aa' },
                },
            ],
        }],
    });
    window.addEventListener('resize', () => chart.resize());
    return chart;
}

export function initLineChart(el: HTMLElement, data: number[], labels: string[]): echarts.ECharts {
    const chart = echarts.init(el);
    chart.setOption({
        grid: { top: 16, right: 16, bottom: 32, left: 48 },
        tooltip: { trigger: 'axis' },
        xAxis: {
            type: 'category',
            data: labels,
            axisLine: { lineStyle: { color: '#e4e4e7' } },
            axisLabel: { color: '#71717a', fontSize: 11 },
        },
        yAxis: {
            type: 'value',
            min: 0, max: 100,
            axisLine: { show: false },
            splitLine: { lineStyle: { color: '#f4f4f5' } },
            axisLabel: { color: '#71717a', fontSize: 11 },
        },
        series: [{
            type: 'line',
            data,
            smooth: true,
            symbol: 'circle',
            symbolSize: 5,
            lineStyle: { color: brand, width: 2 },
            itemStyle: { color: brand },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(207,124,101,0.3)' },
                    { offset: 1, color: 'rgba(207,124,101,0.02)' },
                ]),
            },
        }],
    });
    window.addEventListener('resize', () => chart.resize());
    return chart;
}

// 向后兼容
export const initCharts = (el: HTMLElement) => initRadarChart(el);
