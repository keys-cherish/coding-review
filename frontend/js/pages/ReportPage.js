/**
 * ReportPage - 报告生成与下载
 *
 * 顶部三种格式生成按钮（HTML / PDF / Markdown），下方历史报告列表。
 */
window.ReportPage = (() => {
  const { defineComponent, ref, computed, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const scanId = computed(() => Number(Router.state.params.id));
      const reports = ref([]);
      const generating = ref('');
      const loading = ref(true);

      async function load() {
        loading.value = true;
        try {
          reports.value = await API.listReports(scanId.value);
        } catch (e) {
          Store.error('加载报告列表失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      async function generate(fmt) {
        generating.value = fmt;
        try {
          const r = await API.generateReport(scanId.value, fmt);
          Store.success(fmt.toUpperCase() + ' 报告生成成功');
          await load();
        } catch (e) {
          Store.error('生成失败: ' + e.message);
        } finally {
          generating.value = '';
        }
      }

      function fmt(s) {
        if (!s) return '-';
        return new Date(s).toLocaleString('zh-CN', { hour12: false });
      }

      function fmtIcon(fmt) {
        return ({ html: '🌐', pdf: '📄', md: '📝' })[fmt] || '📦';
      }

      function fmtLabel(fmt) {
        return ({ html: 'HTML 网页', pdf: 'PDF 文档', md: 'Markdown' })[fmt] || fmt;
      }

      return () => {
        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          h('div', { class: 'flex items-center gap-3 mb-6' }, [
            h('button', {
              class: 'btn btn-ghost btn-sm',
              onClick: () => Router.push('/scans/' + scanId.value),
            }, '← 总览'),
            h('h1', { class: 'text-2xl font-bold' }, '检测报告'),
          ]),

          h('div', { class: 'card p-6 mb-6' }, [
            h('div', { class: 'text-sm font-semibold mb-4' }, '生成新报告'),
            h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-4' }, [
              ['html', 'pdf', 'md'].map(fmt =>
                h('button', {
                  key: fmt,
                  class: 'btn btn-primary py-6 text-lg',
                  disabled: generating.value !== '',
                  onClick: () => generate(fmt),
                }, [
                  h('span', { class: 'text-2xl mr-3' }, fmtIcon(fmt)),
                  generating.value === fmt ? '生成中...' : '导出 ' + fmtLabel(fmt),
                ])
              ),
            ]),
            h('div', { class: 'text-app-dim text-xs mt-4' },
              '· HTML：交互式可视化报告，可独立查看 / 转发\n' +
              '· PDF：基于 HTML 转换，便于打印归档\n' +
              '· Markdown：纯文本结构化报告，便于整合到 Wiki / Issue'),
          ]),

          h('div', { class: 'card overflow-hidden' }, [
            h('div', { class: 'p-4 border-b border-app flex justify-between items-center' }, [
              h('div', { class: 'text-sm font-semibold' }, '历史报告'),
              h('span', { class: 'text-app-dim text-xs' }, '共 ' + reports.value.length + ' 份'),
            ]),
            loading.value
              ? h('div', { class: 'flex justify-center py-16' }, h('div', { class: 'loader' }))
              : reports.value.length === 0
                ? h('div', { class: 'p-10 text-center text-app-muted' }, '尚未生成报告')
                : h('div', { class: 'divide-y divide-app' }, reports.value.map(r =>
                    h('div', {
                      class: 'p-4 flex items-center gap-4 hover:bg-card-hover',
                      key: r.id,
                    }, [
                      h('div', { class: 'text-3xl' }, fmtIcon(r.format)),
                      h('div', { class: 'flex-1 min-w-0' }, [
                        h('div', { class: 'font-semibold' },
                          fmtLabel(r.format) + ' · 报告 #' + r.id),
                        h('div', { class: 'text-app-muted text-xs' },
                          '生成于 ' + fmt(r.generated_at)),
                      ]),
                      r.format !== 'pdf' && h('a', {
                        class: 'btn btn-ghost btn-sm',
                        href: API.reportInlineUrl(r.id),
                        target: '_blank',
                      }, '在线查看'),
                      h('a', {
                        class: 'btn btn-primary btn-sm',
                        href: API.reportDownloadUrl(r.id),
                        download: '',
                      }, '下载'),
                    ])
                  )),
          ]),
        ]);
      };
    },
  });
})();
