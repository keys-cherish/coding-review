/**
 * components/charts.js - 基于 ECharts 的可视化组件
 *
 * 包含：
 * - ScoreRadar  雷达图（规范/重复/复杂度）
 * - SeverityPie 严重度饼图
 * - HealthBars  文件健康度横向条形图
 * - HealthHeatmap 文件分布热力图（树状）
 */
(function () {
  const { defineComponent, ref, watch, onMounted, onBeforeUnmount, nextTick, h } = Vue;

  /** 通用：在容器内挂一个 echarts 实例。 */
  function useChart(option) {
    const el = ref(null);
    let chart = null;
    function render() {
      if (!el.value) return;
      if (!chart) chart = echarts.init(el.value, null, { renderer: 'canvas' });
      chart.setOption(option.value, true);
      chart.resize();
    }
    onMounted(() => {
      nextTick(render);
      window.addEventListener('resize', render);
    });
    onBeforeUnmount(() => {
      window.removeEventListener('resize', render);
      if (chart) { chart.dispose(); chart = null; }
    });
    watch(option, () => nextTick(render), { deep: true });
    return el;
  }

  // ---------- 雷达图 ----------
  window.ScoreRadar = defineComponent({
    props: {
      spec: { type: Number, default: 0 },
      duplication: { type: Number, default: 0 },
      complexity: { type: Number, default: 0 },
    },
    setup(props) {
      const option = ref({});
      function build() {
        option.value = {
          backgroundColor: 'transparent',
          tooltip: {},
          radar: {
            indicator: [
              { name: '规范度', max: 100 },
              { name: '重复度', max: 100 },
              { name: '复杂度', max: 100 },
            ],
            shape: 'polygon',
            splitNumber: 4,
            axisName: { color: '#9ba8c4', fontSize: 13 },
            splitLine: { lineStyle: { color: 'rgba(155, 168, 196, 0.15)' } },
            splitArea: { areaStyle: { color: ['rgba(0,212,255,0.02)', 'rgba(0,212,255,0.04)'] } },
            axisLine: { lineStyle: { color: 'rgba(155, 168, 196, 0.2)' } },
          },
          series: [{
            type: 'radar',
            symbolSize: 8,
            data: [{
              value: [props.spec, props.duplication, props.complexity],
              name: '本次评分',
              areaStyle: { color: 'rgba(0, 212, 255, 0.25)' },
              lineStyle: { color: '#00d4ff', width: 2 },
              itemStyle: { color: '#00d4ff' },
            }],
          }],
        };
      }
      watch(() => [props.spec, props.duplication, props.complexity], build, { immediate: true });
      const el = useChart(option);
      return () => h('div', { ref: el, style: 'width: 100%; height: 320px;' });
    },
  });

  // ---------- 严重度分布饼 ----------
  window.SeverityPie = defineComponent({
    props: {
      counts: { type: Object, default: () => ({ error: 0, warning: 0, info: 0 }) },
    },
    setup(props) {
      const option = ref({});
      function build() {
        option.value = {
          tooltip: { trigger: 'item' },
          legend: { bottom: 0, textStyle: { color: '#9ba8c4' } },
          series: [{
            name: '问题分布',
            type: 'pie',
            radius: ['58%', '78%'],
            avoidLabelOverlap: false,
            label: { show: true, formatter: '{b}\n{c}', color: '#e8ecf3' },
            labelLine: { length: 12, length2: 8 },
            data: [
              { value: props.counts.error || 0,   name: '严重', itemStyle: { color: '#ff5470' } },
              { value: props.counts.warning || 0, name: '警告', itemStyle: { color: '#ffb84d' } },
              { value: props.counts.info || 0,    name: '提示', itemStyle: { color: '#7dd3fc' } },
            ].filter(i => i.value > 0),
          }],
        };
      }
      watch(() => props.counts, build, { immediate: true, deep: true });
      const el = useChart(option);
      return () => h('div', { ref: el, style: 'width: 100%; height: 280px;' });
    },
  });

  // ---------- 横向条形：触发最多的规则 ----------
  window.RuleBar = defineComponent({
    props: {
      items: { type: Array, default: () => [] },  // [{rule_code, count}]
    },
    setup(props) {
      const option = ref({});
      function build() {
        const data = (props.items || []).slice(0, 10).reverse();
        option.value = {
          tooltip: { trigger: 'axis' },
          grid: { left: 130, right: 20, top: 10, bottom: 30 },
          xAxis: {
            type: 'value',
            axisLabel: { color: '#9ba8c4' },
            axisLine: { lineStyle: { color: 'rgba(155,168,196,.3)' } },
            splitLine: { lineStyle: { color: 'rgba(155,168,196,.1)' } },
          },
          yAxis: {
            type: 'category',
            data: data.map(d => d.rule_code),
            axisLabel: { color: '#e8ecf3', fontFamily: 'JetBrains Mono, Consolas, monospace' },
            axisLine: { lineStyle: { color: 'rgba(155,168,196,.3)' } },
          },
          series: [{
            type: 'bar',
            data: data.map(d => d.count),
            barMaxWidth: 18,
            itemStyle: {
              color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
                colorStops: [
                  { offset: 0, color: '#2563eb' },
                  { offset: 1, color: '#00d4ff' },
                ]
              },
              borderRadius: [0, 6, 6, 0],
            },
            label: { show: true, position: 'right', color: '#9ba8c4' },
          }],
        };
      }
      watch(() => props.items, build, { immediate: true, deep: true });
      const el = useChart(option);
      return () => h('div', { ref: el, style: 'width: 100%; height: 360px;' });
    },
  });

  // ---------- 文件健康度热力树状图 ----------
  window.HealthHeatmap = defineComponent({
    props: {
      files: { type: Array, default: () => [] },  // [{path, health, issues}]
    },
    setup(props) {
      const option = ref({});
      function build() {
        const data = (props.files || []).map(f => ({
          name: f.path,
          value: f.issues || 1,
          health: f.health || 0,
          itemStyle: {
            color: f.health >= 80 ? '#5ce28b'
                 : f.health >= 60 ? '#00d4ff'
                 : f.health >= 40 ? '#ffb84d'
                 : '#ff5470',
            borderColor: 'rgba(10, 14, 26, 0.6)',
            borderWidth: 2,
          },
          label: { color: '#0a0e1a', fontWeight: 600 },
        }));
        option.value = {
          tooltip: {
            formatter: (info) => `<b>${info.data.name}</b><br/>问题数 ${info.data.value} · 健康度 ${info.data.health.toFixed(1)}`,
          },
          series: [{
            type: 'treemap',
            roam: false,
            nodeClick: false,
            breadcrumb: { show: false },
            data,
            label: { show: true, formatter: '{b}', overflow: 'truncate' },
            upperLabel: { show: false },
          }],
        };
      }
      watch(() => props.files, build, { immediate: true, deep: true });
      const el = useChart(option);
      return () => h('div', { ref: el, style: 'width: 100%; height: 360px;' });
    },
  });

  // ---------- 复杂度气泡 ----------
  window.ComplexityBubble = defineComponent({
    props: {
      metrics: { type: Array, default: () => [] }, // [{function_name, lines, cyclomatic, cognitive, risk_level}]
    },
    setup(props) {
      const option = ref({});
      function build() {
        const colorMap = { low: '#5ce28b', medium: '#ffb84d', high: '#ff8c4a', critical: '#ff5470' };
        const data = (props.metrics || []).map(m => ({
          name: m.function_name,
          value: [m.lines, m.cyclomatic, m.cognitive],
          itemStyle: { color: colorMap[m.risk_level] || '#9ba8c4', opacity: 0.85 },
        }));
        option.value = {
          tooltip: {
            formatter: (p) => `<b>${p.name}</b><br/>行数 ${p.value[0]} · CC ${p.value[1]} · 认知 ${p.value[2]}`,
          },
          grid: { left: 50, right: 20, top: 30, bottom: 36 },
          xAxis: { name: '行数', nameTextStyle: { color: '#9ba8c4' }, axisLabel: { color: '#9ba8c4' } },
          yAxis: { name: '圈复杂度', nameTextStyle: { color: '#9ba8c4' }, axisLabel: { color: '#9ba8c4' } },
          series: [{
            type: 'scatter',
            symbolSize: (val) => Math.max(8, Math.min(40, val[2] * 1.5)),
            data,
          }],
        };
      }
      watch(() => props.metrics, build, { immediate: true, deep: true });
      const el = useChart(option);
      return () => h('div', { ref: el, style: 'width: 100%; height: 320px;' });
    },
  });

})();
