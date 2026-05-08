/**
 * ComplexityPage - 复杂度排行榜
 *
 * 顶部气泡图（行数 / 圈复杂度 / 认知负担三维），下方表格列出 Top N 函数。
 */
window.ComplexityPage = (() => {
  const { defineComponent, ref, computed, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const scanId = computed(() => Number(Router.state.params.id));
      const metrics = ref([]);
      const loading = ref(true);

      async function load() {
        loading.value = true;
        try {
          metrics.value = await API.listComplexity(scanId.value, 100);
        } catch (e) {
          Store.error('加载复杂度数据失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      const stats = computed(() => {
        const m = metrics.value;
        if (m.length === 0) return { count: 0, avgCC: 0, maxCC: 0, critical: 0 };
        return {
          count: m.length,
          avgCC: m.reduce((s, x) => s + x.cyclomatic, 0) / m.length,
          maxCC: m.reduce((mx, x) => Math.max(mx, x.cyclomatic), 0),
          critical: m.filter(x => x.risk_level === 'critical').length,
        };
      });

      function riskBadge(level) {
        const map = {
          low: { c: 'badge-success', t: '低风险' },
          medium: { c: 'badge-info', t: '中等' },
          high: { c: 'badge-warning', t: '偏高' },
          critical: { c: 'badge-error', t: '严重' },
        };
        const v = map[level] || map.medium;
        return h('span', { class: 'badge ' + v.c }, v.t);
      }

      return () => {
        const m = metrics.value;
        const st = stats.value;

        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          h('div', { class: 'flex items-center gap-3 mb-6' }, [
            h('button', {
              class: 'btn btn-ghost btn-sm',
              onClick: () => Router.push('/scans/' + scanId.value),
            }, '← 总览'),
            h('h1', { class: 'text-2xl font-bold' }, '复杂度排行榜'),
          ]),

          h('div', { class: 'grid grid-cols-2 md:grid-cols-4 gap-3 mb-6' }, [
            h(StatCard, { label: '函数总数', value: st.count, color: 'primary' }),
            h(StatCard, { label: '平均圈复杂度', value: st.avgCC.toFixed(1), color: 'success' }),
            h(StatCard, { label: '最高圈复杂度', value: st.maxCC, color: 'danger' }),
            h(StatCard, { label: '严重复杂', value: st.critical, hint: '需立即重构', color: 'warning' }),
          ]),

          h('div', { class: 'card p-5 mb-6' }, [
            h('div', { class: 'text-sm font-semibold mb-3' }, '函数复杂度分布（X 行数 · Y 圈复杂度 · 大小=认知负担）'),
            m.length === 0
              ? h('div', { class: 'text-app-muted text-center py-12' }, '暂无数据')
              : h(ComplexityBubble, { metrics: m }),
          ]),

          h('div', { class: 'card overflow-hidden' }, [
            h('div', { class: 'p-4 border-b border-app' }, [
              h('div', { class: 'text-sm font-semibold' }, '复杂度 Top ' + Math.min(100, m.length)),
            ]),
            loading.value
              ? h('div', { class: 'flex justify-center py-16' }, h('div', { class: 'loader' }))
              : m.length === 0
                ? h('div', { class: 'p-10 text-center text-app-muted' }, '暂无函数数据')
                : h('div', { class: 'overflow-x-auto' }, [
                    h('table', { class: 'min-w-full text-sm' }, [
                      h('thead', { class: 'bg-app text-app-muted text-xs uppercase' }, [
                        h('tr', null, [
                          h('th', { class: 'p-3 text-left' }, '#'),
                          h('th', { class: 'p-3 text-left' }, '函数'),
                          h('th', { class: 'p-3 text-right' }, '行数'),
                          h('th', { class: 'p-3 text-right' }, '圈复杂度'),
                          h('th', { class: 'p-3 text-right' }, '认知负担'),
                          h('th', { class: 'p-3 text-right' }, '嵌套'),
                          h('th', { class: 'p-3 text-right' }, '参数'),
                          h('th', { class: 'p-3 text-center' }, '风险'),
                        ]),
                      ]),
                      h('tbody', null, m.map((it, i) =>
                        h('tr', {
                          class: 'border-t border-app hover:bg-card-hover',
                          key: it.id,
                        }, [
                          h('td', { class: 'p-3 text-app-dim' }, i + 1),
                          h('td', { class: 'p-3 font-mono' }, [
                            h('div', null, it.function_name),
                            h('div', { class: 'text-app-dim text-xs' },
                              ':' + it.start_line + '-' + it.end_line),
                          ]),
                          h('td', { class: 'p-3 text-right' }, it.lines),
                          h('td', { class: 'p-3 text-right font-bold text-warning' }, it.cyclomatic),
                          h('td', { class: 'p-3 text-right' }, it.cognitive),
                          h('td', { class: 'p-3 text-right' }, it.nesting_depth),
                          h('td', { class: 'p-3 text-right' }, it.parameters),
                          h('td', { class: 'p-3 text-center' }, riskBadge(it.risk_level)),
                        ])
                      )),
                    ]),
                  ]),
          ]),
        ]);
      };
    },
  });
})();
