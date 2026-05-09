import * as echarts from 'echarts';

// 保存定时器和图表实例，方便在路由切换时清理，防止内存泄漏
let trendInterval: number | undefined;
let chartInstances: echarts.ECharts[] = [];

export function initCharts() {
    // 1. 清理之前的状态
    if (trendInterval) clearInterval(trendInterval);
    chartInstances.forEach(c => c.dispose());
    chartInstances = [];

    const brandColor = '#cf7c65';
    const brandLight = 'rgba(207, 124, 101, 0.2)';

    // === 动态演进折线图 ===
    const trendDom = document.getElementById('trendChart');
    if (trendDom) {
        const trendChart = echarts.init(trendDom);
        chartInstances.push(trendChart);

        const dataAxis: string[] = [];
        const dataValue: number[] = [];
        let now = new Date();

        // 初始化过去 30 个数据点
        for (let i = 0; i < 30; i++) {
            dataAxis.push(now.toLocaleTimeString('zh-CN', { hour12: false }));
            dataValue.push(85 + Math.random() * 10);
            now = new Date(now.getTime() + 2000);
        }

        trendChart.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
            xAxis: { type: 'category', boundaryGap: false, data: dataAxis, axisLine: { lineStyle: { color: '#ccc' } } },
            yAxis: { type: 'value', min: 70, max: 100, splitLine: { lineStyle: { type: 'dashed', color: '#eee' } } },
            series: [{
                name: '代码评分', type: 'line', smooth: true, symbol: 'none',
                lineStyle: { width: 3, color: brandColor },
                areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: brandLight }, { offset: 1, color: 'rgba(255,255,255,0)' }]) },
                data: dataValue
            }]
        });

        // 启动流式数据模拟
        trendInterval = window.setInterval(() => {
            const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
            const randomVal = 85 + Math.random() * 10;
            dataAxis.shift(); dataAxis.push(time);
            dataValue.shift(); dataValue.push(randomVal);
            trendChart.setOption({ xAxis: { data: dataAxis }, series: [{ data: dataValue }] });
        }, 2000);
    }

    // === 五维雷达图 ===
    const radarDom = document.getElementById('radarChart');
    if (radarDom) {
        const radarChart = echarts.init(radarDom);
        chartInstances.push(radarChart);

        radarChart.setOption({
            tooltip: {},
            radar: {
                indicator: [
                    { name: '规范性', max: 100 }, { name: '复杂度', max: 100 },
                    { name: '安全性', max: 100 }, { name: '重复率', max: 100 }, { name: '可维护性', max: 100 }
                ],
                axisName: { color: '#666', fontFamily: 'Georgia' },
                splitArea: { areaStyle: { color: ['#f9f9f9', '#ffffff'] } }
            },
            series: [{
                type: 'radar',
                data: [{
                    value: [92, 85, 95, 78, 88], name: '当前分支评分',
                    lineStyle: { color: brandColor, width: 2 },
                    itemStyle: { color: brandColor },
                    areaStyle: { color: brandLight }
                }]
            }]
        });
    }

    // === 响应式处理 ===
    window.addEventListener('resize', () => {
        chartInstances.forEach(c => c.resize());
    });
}
