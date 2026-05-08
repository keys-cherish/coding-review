/**
 * ScanResultPage - 扫描结果总览
 *
 * 展示一个扫描任务的全景：评分雷达、严重度分布、问题文件 Top10、热门规则、入口快链。
 */
window.ScanResultPage = (() => {
  const { defineComponent, ref, computed, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const scanId = computed(() => Number(Router.state.params.id));
      const scan = ref(null);
      const summary = ref(null);
      const loading = ref(true);

      async function load() {
        loading.value = true;
        try {
          const [s, sum] = await Promise.all([
            API.getScan(scanId.value),
            API.issueSummary(scanId.value),
          ]);
          scan.value = s;
          summary.value = sum;
        } catch (e) {
          Store.error('加载结果失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      function navTo(name) {
        Router.push(`/scans/${scanId.value}/${name}`);
      }

      return () => {
        if (loading.value) {
          return h('div', { class: 'min-h-screen flex items-center justify-center' },
            h('div', { class: 'loader' }));
        }
        if (!scan.value) {
          return h('div', { class: 'max-w-5xl mx-auto p-10 text-center text-app-muted' },
            '扫描结果不存在或已被清除');
        }

        const s = scan.value;
        const counts = {
          error: s.error_count,
          warning: s.warning_count,
          info: s.info_count,
        };
        const isDone = s.status === 'done';
        const sum = summary.value || { top_rules: [], top_files: [] };

        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          h('div', { class: 'flex items-center justify-between mb-6' }, [
            h('div', { class: 'flex items-center gap-3' }, [
              h('button', {
                class: 'btn btn-ghost btn-sm',
                onClick: () => history.back(),
              }, '← 返回'),
              h('h1', { class: 'text-2xl font-bold' }, `扫描 #${s.id} · 结果总览`),
              s.status !== 'done' && h('span', { class: 'badge badge-warning' }, s.status),
            ]),
            isDone && h('div', { class: 'flex gap-2' }, [
              h('button', { class: 'btn btn-ghost', onClick: () => navTo('issues') }, '问题清单'),
              h('button', { class: 'btn btn-ghost', onClick: () => navTo('duplications') }, '重复代码'),
              h('button', { class: 'btn btn-ghost', onClick: () => navTo('complexity') }, '复杂度'),
              h('button', { class: 'btn btn-primary', onClick: () => navTo('report') }, '导出报告'),
            ]),
          ]),

          h('div', { class: 'grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6' }, [
            h('div', { class: 'card p-6 lg:col-span-1' }, [
              h('div', { class: 'text-app-muted text-xs uppercase tracking-wider mb-3' }, '综合评分'),
              h('div', { class: 'flex items-end gap-3' }, [
                h('span', { class: 'score-big' }, [h(AnimatedNumber, { value: s.overall_score, decimals: 1 })]),
                h('span', { class: 'text-app-muted text-2xl mb-2' }, '/100'),
                h('div', { class: 'ml-auto' }, h(GradeBadge, { grade: s.grade })),
              ]),
              h('div', { class: 'grid grid-cols-3 gap-3 mt-6 pt-4 border-t border-app' }, [
                scoreCell('规范度', s.spec_score, 'primary'),
                scoreCell('重复度', s.dup_score, 'success'),
                scoreCell('复杂度', s.complexity_score, 'warning'),
              ]),
            ]),
            h('div', { class: 'card p-5 lg:col-span-2' }, [
              h('div', { class: 'text-sm font-semibold mb-2 flex justify-between' }, [
                h('span', '三维雷达'),
                h('span', { class: 'text-app-dim text-xs' }, '满分 100'),
              ]),
              h(ScoreRadar, {
                spec: s.spec_score,
                duplication: s.dup_score,
                complexity: s.complexity_score,
              }),
            ]),
          ]),

          h('div', { class: 'grid grid-cols-2 md:grid-cols-4 gap-3 mb-6' }, [
            h(StatCard, { label: '问题总数', value: s.total_issues, color: 'primary' }),
            h(StatCard, { label: '严重', value: s.error_count, color: 'danger' }),
            h(StatCard, { label: '警告', value: s.warning_count, color: 'warning' }),
            h(StatCard, { label: '提示', value: s.info_count, color: 'success' }),
          ]),
          h('div', { class: 'grid grid-cols-2 md:grid-cols-4 gap-3 mb-6' }, [
            h(StatCard, { label: '重复率', value: (s.duplication_rate * 100).toFixed(1) + '%', color: 'warning' }),
            h(StatCard, { label: '平均复杂度', value: s.avg_complexity.toFixed(1), color: 'primary' }),
            h(StatCard, { label: '最高复杂度', value: s.max_complexity, color: 'danger' }),
            h(StatCard, { label: '扫描状态', value: statusLabel(s.status), color: isDone ? 'success' : 'warning' }),
          ]),

          h('div', { class: 'grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6' }, [
            h('div', { class: 'card p-5' }, [
              h('div', { class: 'text-sm font-semibold mb-3' }, '问题严重度分布'),
              s.total_issues === 0
                ? h('div', { class: 'text-app-muted text-center py-12' }, '🎉 没有问题')
                : h(SeverityPie, { counts }),
            ]),
            h('div', { class: 'card p-5' }, [
              h('div', { class: 'text-sm font-semibold mb-3' }, '触发最多的规则 Top 10'),
              sum.top_rules.length === 0
                ? h('div', { class: 'text-app-muted text-center py-12' }, '暂无数据')
                : h(RuleBar, { items: sum.top_rules }),
            ]),
          ]),

          h('div', { class: 'card p-5 mb-6' }, [
            h('div', { class: 'flex justify-between items-center mb-3' }, [
              h('div', { class: 'text-sm font-semibold' }, '问题文件 Top 20 · 健康度热力'),
              h('div', { class: 'text-app-dim text-xs' }, '面积=问题数 · 颜色=健康度'),
            ]),
            sum.top_files.length === 0
              ? h('div', { class: 'text-app-muted text-center py-12' }, '没有问题文件')
              : h(HealthHeatmap, { files: sum.top_files }),
          ]),

          s.status === 'failed' && s.error_msg && h('div', { class: 'card p-5 border-l-4 border-danger' }, [
            h('div', { class: 'text-sm font-semibold mb-2 text-danger' }, '扫描失败信息'),
            h('pre', { class: 'text-xs text-app-muted whitespace-pre-wrap' }, s.error_msg),
          ]),
        ]);
      };
    },
  });

  function scoreCell(label, value, color) {
    const colorMap = {
      primary: 'var(--primary)',
      success: 'var(--accent)',
      warning: 'var(--warning)',
      danger: 'var(--danger)',
    };
    return Vue.h('div', null, [
      Vue.h('div', { class: 'text-app-muted text-xs mb-1' }, label),
      Vue.h('div', { class: 'text-2xl font-bold', style: `color: ${colorMap[color]}` },
        value !== undefined && value !== null ? value.toFixed(1) : '-'),
    ]);
  }

  function statusLabel(s) {
    return ({ pending: '排队中', running: '执行中', done: '已完成', failed: '失败' })[s] || s;
  }
})();
