/**
 * IssuesPage - 问题清单
 *
 * 左侧过滤器：严重度、规则代码、关键词
 * 右侧问题卡片：文件、行号、严重度、规则、消息、代码片段、修改建议
 */
window.IssuesPage = (() => {
  const { defineComponent, ref, computed, watch, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const scanId = computed(() => Number(Router.state.params.id));
      const issues = ref([]);
      const summary = ref(null);
      const loading = ref(true);
      const filterSeverity = ref('');
      const filterRule = ref('');
      const keyword = ref('');
      const expandedIds = ref(new Set());

      async function load() {
        loading.value = true;
        try {
          const params = { limit: 1000 };
          if (filterSeverity.value) params.severity = filterSeverity.value;
          if (filterRule.value) params.rule_code = filterRule.value;
          const list = await API.listIssues(scanId.value, params);
          if (!summary.value) summary.value = await API.issueSummary(scanId.value);
          issues.value = list;
        } catch (e) {
          Store.error('加载问题列表失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);
      watch([filterSeverity, filterRule], load);

      const filteredIssues = computed(() => {
        if (!keyword.value.trim()) return issues.value;
        const k = keyword.value.toLowerCase();
        return issues.value.filter(i =>
          (i.file_path || '').toLowerCase().includes(k) ||
          (i.message || '').toLowerCase().includes(k) ||
          (i.rule_code || '').toLowerCase().includes(k)
        );
      });

      function toggleExpand(id) {
        const s = new Set(expandedIds.value);
        if (s.has(id)) s.delete(id); else s.add(id);
        expandedIds.value = s;
      }

      function severityCount(sev) {
        const by = summary.value && summary.value.by_severity;
        return (by && by[sev]) || 0;
      }

      function getLanguage(path) {
        if (!path) return 'plaintext';
        if (path.endsWith('.py')) return 'python';
        if (path.endsWith('.java')) return 'java';
        return 'plaintext';
      }

      function renderSidebar(topRules) {
        return h('div', { class: 'lg:col-span-1' }, [
          h('div', { class: 'card p-4 mb-3' }, [
            h('div', { class: 'text-sm font-semibold mb-3' }, '关键词搜索'),
            h('input', {
              class: 'input', placeholder: '路径 / 消息 / 规则码',
              value: keyword.value,
              onInput: (e) => keyword.value = e.target.value,
            }),
          ]),
          h('div', { class: 'card p-4 mb-3' }, [
            h('div', { class: 'text-sm font-semibold mb-3' }, '严重度'),
            ['', 'error', 'warning', 'info'].map(sev =>
              h('label', {
                class: 'flex items-center gap-2 py-2 cursor-pointer ' +
                  (filterSeverity.value === sev ? 'text-primary' : 'text-app-muted'),
              }, [
                h('input', {
                  type: 'radio', name: 'sev',
                  checked: filterSeverity.value === sev,
                  onChange: () => filterSeverity.value = sev,
                }),
                h('span', null, sev === ''
                  ? '全部 (' + issues.value.length + ')'
                  : sevLabel(sev) + ' (' + severityCount(sev) + ')'),
              ])
            ),
          ]),
          h('div', { class: 'card p-4' }, [
            h('div', { class: 'text-sm font-semibold mb-3' }, '热门规则'),
            topRules.length === 0
              ? h('div', { class: 'text-app-dim text-xs' }, '暂无')
              : h('div', null, [
                  filterRule.value && h('button', {
                    class: 'btn btn-ghost btn-sm w-full mb-2',
                    onClick: () => filterRule.value = '',
                  }, '清除规则筛选'),
                  ...topRules.slice(0, 12).map(r =>
                    h('div', {
                      class: 'cursor-pointer py-1 px-2 rounded text-xs flex justify-between mb-1 ' +
                        (filterRule.value === r.rule_code
                          ? 'bg-primary text-white'
                          : 'text-app-muted hover:bg-card-hover'),
                      onClick: () => filterRule.value = r.rule_code,
                    }, [
                      h('span', { class: 'font-mono' }, r.rule_code),
                      h('span', null, r.count),
                    ])
                  ),
                ]),
          ]),
        ]);
      }

      function renderIssue(it) {
        const expanded = expandedIds.value.has(it.id);
        return h('div', { class: 'card overflow-hidden', key: it.id }, [
          h('div', {
            class: 'p-4 cursor-pointer hover:bg-card-hover',
            onClick: () => toggleExpand(it.id),
          }, [
            h('div', { class: 'flex items-start gap-3' }, [
              h(SeverityBadge, { severity: it.severity }),
              h('div', { class: 'flex-1 min-w-0' }, [
                h('div', { class: 'flex items-center gap-2 mb-1 flex-wrap' }, [
                  h('span', { class: 'font-mono text-xs text-primary' }, it.rule_code),
                  h('span', { class: 'badge bg-app text-app-muted text-xs' }, it.category),
                  h('span', { class: 'text-app-dim text-xs' },
                    it.file_path + ':' + it.line),
                ]),
                h('div', { class: 'text-sm' }, it.message),
              ]),
              h('div', { class: 'text-app-dim text-xs' }, expanded ? '▲' : '▼'),
            ]),
          ]),
          expanded && h('div', { class: 'border-t border-app p-4 bg-app' }, [
            it.code_snippet && h('div', { class: 'mb-3' }, [
              h('div', { class: 'text-xs text-app-muted mb-2' }, '相关代码'),
              h(CodeViewer, {
                code: it.code_snippet,
                language: getLanguage(it.file_path),
                startLine: Math.max(1, it.line - 2),
                highlightLine: it.line,
              }),
            ]),
            it.suggestion && h('div', { class: 'card-inset p-3' }, [
              h('div', { class: 'text-xs text-app-muted mb-1' }, '💡 修改建议'),
              h('div', { class: 'text-sm', style: 'white-space: pre-wrap' }, it.suggestion),
            ]),
          ]),
        ]);
      }

      return () => {
        const list = filteredIssues.value;
        const topRules = (summary.value && summary.value.top_rules) || [];

        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          h('div', { class: 'flex items-center gap-3 mb-6' }, [
            h('button', {
              class: 'btn btn-ghost btn-sm',
              onClick: () => Router.push('/scans/' + scanId.value),
            }, '← 总览'),
            h('h1', { class: 'text-2xl font-bold' }, '问题清单'),
            h('span', { class: 'text-app-muted ml-auto' },
              '共 ' + list.length + ' / ' + issues.value.length + ' 条'),
          ]),

          h('div', { class: 'grid grid-cols-1 lg:grid-cols-4 gap-4' }, [
            renderSidebar(topRules),
            h('div', { class: 'lg:col-span-3' }, [
              loading.value
                ? h('div', { class: 'flex justify-center py-16' }, h('div', { class: 'loader' }))
                : list.length === 0
                  ? h('div', { class: 'card p-10 text-center text-app-muted' }, [
                      h('div', { class: 'text-4xl mb-3' }, '🎉'),
                      h('div', null, '当前过滤条件下没有问题'),
                    ])
                  : h('div', { class: 'space-y-3' }, list.map(renderIssue)),
            ]),
          ]),
        ]);
      };
    },
  });

  function sevLabel(s) {
    return ({ error: '严重', warning: '警告', info: '提示' })[s] || s;
  }
})();
