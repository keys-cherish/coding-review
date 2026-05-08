/**
 * DuplicationsPage - 重复代码块清单
 *
 * 列出所有重复代码片段，按行数倒序。每个块展开后展示出现位置（文件、行号区间）。
 */
window.DuplicationsPage = (() => {
  const { defineComponent, ref, computed, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const scanId = computed(() => Number(Router.state.params.id));
      const dups = ref([]);
      const loading = ref(true);
      const expandedIds = ref(new Set());

      async function load() {
        loading.value = true;
        try {
          dups.value = await API.listDuplications(scanId.value);
        } catch (e) {
          Store.error('加载重复块失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      function parseOccurrences(it) {
        try {
          return JSON.parse(it.occurrences_json || '[]');
        } catch {
          return [];
        }
      }

      function toggle(id) {
        const s = new Set(expandedIds.value);
        if (s.has(id)) s.delete(id); else s.add(id);
        expandedIds.value = s;
      }

      const stats = computed(() => {
        const list = dups.value;
        return {
          blocks: list.length,
          totalLines: list.reduce((s, d) => s + d.line_length * d.occurrences, 0),
          maxLines: list.reduce((m, d) => Math.max(m, d.line_length), 0),
          avgOccurrences: list.length === 0 ? 0 :
            list.reduce((s, d) => s + d.occurrences, 0) / list.length,
        };
      });

      return () => {
        const list = dups.value;
        const st = stats.value;

        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          h('div', { class: 'flex items-center gap-3 mb-6' }, [
            h('button', {
              class: 'btn btn-ghost btn-sm',
              onClick: () => Router.push('/scans/' + scanId.value),
            }, '← 总览'),
            h('h1', { class: 'text-2xl font-bold' }, '重复代码块'),
          ]),

          h('div', { class: 'grid grid-cols-2 md:grid-cols-4 gap-3 mb-6' }, [
            h(StatCard, { label: '重复代码块', value: st.blocks, color: 'primary' }),
            h(StatCard, { label: '累计重复行', value: st.totalLines, color: 'warning' }),
            h(StatCard, { label: '最长块行数', value: st.maxLines, color: 'danger' }),
            h(StatCard, { label: '平均重复次数', value: st.avgOccurrences.toFixed(1), color: 'success' }),
          ]),

          loading.value
            ? h('div', { class: 'flex justify-center py-16' }, h('div', { class: 'loader' }))
            : list.length === 0
              ? h('div', { class: 'card p-10 text-center text-app-muted' }, [
                  h('div', { class: 'text-4xl mb-3' }, '🎉'),
                  h('div', null, '没有发现重复代码'),
                ])
              : h('div', { class: 'space-y-3' }, list.map(d => {
                  const expanded = expandedIds.value.has(d.id);
                  const occs = parseOccurrences(d);
                  return h('div', { class: 'card overflow-hidden', key: d.id }, [
                    h('div', {
                      class: 'p-4 cursor-pointer hover:bg-card-hover',
                      onClick: () => toggle(d.id),
                    }, [
                      h('div', { class: 'flex items-center gap-3 flex-wrap' }, [
                        h('span', { class: 'badge badge-warning' },
                          d.line_length + ' 行'),
                        h('span', { class: 'text-app-muted text-sm' },
                          '出现 ' + d.occurrences + ' 次'),
                        h('span', { class: 'text-app-dim text-xs' },
                          'token=' + d.token_length + ' · ' + d.detection_method),
                        h('span', { class: 'font-mono text-xs text-app-dim ml-auto' },
                          d.fingerprint.slice(0, 12)),
                        h('span', { class: 'text-app-dim text-xs' },
                          expanded ? '▲' : '▼'),
                      ]),
                    ]),
                    expanded && h('div', { class: 'border-t border-app p-4 bg-app' }, [
                      h('div', { class: 'text-xs text-app-muted mb-2' },
                        '出现位置（共 ' + occs.length + '）'),
                      h('div', { class: 'space-y-1' }, occs.map((o, idx) =>
                        h('div', {
                          class: 'flex items-center gap-2 text-sm font-mono py-1 px-2 rounded hover:bg-card-hover',
                          key: idx,
                        }, [
                          h('span', { class: 'text-primary' }, '#' + (idx + 1)),
                          h('span', null, o.path || o.file || '(unknown)'),
                          h('span', { class: 'text-app-muted' },
                            ':' + (o.start_line || o.line || '?') +
                            (o.end_line ? '-' + o.end_line : '')),
                        ])
                      )),
                    ]),
                  ]);
                })),
        ]);
      };
    },
  });
})();
