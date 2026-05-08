/**
 * ScanProgressPage - 扫描进度（WebSocket 实时推送）
 */
window.ScanProgressPage = (() => {
  const { defineComponent, ref, computed, onMounted, onBeforeUnmount, h } = Vue;

  return defineComponent({
    setup() {
      const scanId = computed(() => Number(Router.state.params.id));
      const scan = ref(null);
      const events = ref([]);  // 实时滚动文字
      const ws = ref(null);
      let pollTimer = null;

      async function refresh() {
        try {
          const s = await API.getScan(scanId.value);
          scan.value = s;
          if (s.status === 'done') {
            cleanup();
            setTimeout(() => Router.push(`/scans/${scanId.value}`), 600);
          } else if (s.status === 'failed') {
            cleanup();
          }
        } catch {}
      }

      function cleanup() {
        if (ws.value) { try { ws.value.close(); } catch {} ws.value = null; }
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      }

      onMounted(() => {
        refresh();
        ws.value = API.wsScanProgress(scanId.value, (msg) => {
          if (msg.message) {
            events.value.unshift({ time: new Date(), text: msg.message });
            if (events.value.length > 40) events.value.pop();
          }
          if (scan.value) {
            scan.value = { ...scan.value, ...msg, total_issues: msg.issues_found ?? scan.value.total_issues };
          }
          if (msg.status === 'done' || msg.status === 'failed') {
            setTimeout(refresh, 250);
          }
        });
        pollTimer = setInterval(refresh, 2500);
      });
      onBeforeUnmount(cleanup);

      return () => {
        if (!scan.value) {
          return h('div', { class: 'flex justify-center py-20' }, h('div', { class: 'loader' }));
        }
        const s = scan.value;
        const pct = (s.progress * 100).toFixed(1);
        return h('div', { class: 'max-w-4xl mx-auto px-6 py-10' }, [
          h('h1', { class: 'text-2xl font-bold mb-2' }, [
            '🔍 扫描进行中 ',
            h('span', { class: 'text-app-dim text-mono text-base' }, `#${s.id}`),
          ]),
          h('p', { class: 'text-app-muted mb-6' }, '稍等几秒，AI 正在为你的代码做"全身体检"...'),

          // 大进度卡
          h('div', { class: 'card p-8 mb-6' }, [
            h('div', { class: 'flex justify-between items-end mb-3' }, [
              h('div', null, [
                h('div', { class: 'text-app-muted text-xs uppercase tracking-wider mb-1' }, '当前阶段'),
                h('div', { class: 'text-lg font-semibold' },
                  s.status === 'running' ? '🚀 分析中' :
                  s.status === 'pending' ? '⏳ 等待启动' :
                  s.status === 'failed'  ? '❌ 扫描失败' : '✅ 已完成'),
              ]),
              h('div', { class: 'text-right' }, [
                h('div', { class: 'text-3xl font-bold text-primary' }, [pct, h('span', { class: 'text-app-muted text-base' }, '%')]),
              ]),
            ]),
            h(ProgressBar, { progress: s.progress }),

            s.current_file && h('div', { class: 'mt-4 text-sm' }, [
              h('span', { class: 'text-app-muted' }, '正在处理: '),
              h('code', { class: 'text-mono text-primary' }, s.current_file),
            ]),

            h('div', { class: 'grid grid-cols-3 gap-4 mt-6' }, [
              h('div', { class: 'card-2 rounded-lg p-3' }, [
                h('div', { class: 'text-app-dim text-xs mb-1' }, '已发现问题'),
                h('div', { class: 'text-2xl font-bold text-warning' }, s.total_issues || 0),
              ]),
              h('div', { class: 'card-2 rounded-lg p-3' }, [
                h('div', { class: 'text-app-dim text-xs mb-1' }, '错误'),
                h('div', { class: 'text-2xl font-bold text-danger' }, s.error_count || 0),
              ]),
              h('div', { class: 'card-2 rounded-lg p-3' }, [
                h('div', { class: 'text-app-dim text-xs mb-1' }, '警告'),
                h('div', { class: 'text-2xl font-bold' }, s.warning_count || 0),
              ]),
            ]),
          ]),

          s.error_msg && h('div', { class: 'card p-4 mb-6 border-danger' }, [
            h('div', { class: 'text-danger font-semibold mb-1' }, '错误'),
            h('div', { class: 'text-app-muted text-sm' }, s.error_msg),
          ]),

          h('div', { class: 'card p-5' }, [
            h('div', { class: 'flex justify-between items-center mb-3' }, [
              h('h3', { class: 'font-semibold' }, '🔄 实时事件流'),
              h('span', { class: 'text-app-dim text-xs' }, 'WebSocket 推送'),
            ]),
            events.value.length === 0
              ? h('div', { class: 'text-app-muted text-sm' }, '等待事件...')
              : h('div', { class: 'space-y-1 max-h-80 overflow-y-auto text-sm' },
                  events.value.map((ev, i) => h('div', {
                    key: i,
                    class: 'flex gap-3 py-1 px-2 hover:bg-card-3 rounded'
                  }, [
                    h('span', { class: 'text-app-dim text-xs text-mono' },
                      ev.time.toLocaleTimeString('zh-CN', { hour12: false })),
                    h('span', { class: 'text-app-muted' }, ev.text),
                  ]))
                ),
          ]),
        ]);
      };
    },
  });
})();
