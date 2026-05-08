/**
 * ProjectDetailPage - 项目详情：版本列表 + 操作入口
 */
window.ProjectDetailPage = (() => {
  const { defineComponent, ref, computed, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const project = ref(null);
      const versions = ref([]);
      const scansByVersion = ref({});
      const loading = ref(true);

      const projectId = computed(() => Number(Router.state.params.id));

      async function load() {
        loading.value = true;
        try {
          const [p, vs] = await Promise.all([
            API.getProject(projectId.value),
            API.listVersions(projectId.value),
          ]);
          project.value = p;
          versions.value = vs;

          const map = {};
          for (const v of vs) {
            try {
              map[v.id] = await API.listScans(v.id);
            } catch {}
          }
          scansByVersion.value = map;
        } catch (e) {
          Store.error('加载失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      async function startScan(versionId) {
        try {
          const task = await API.startScan(versionId);
          Store.success(`扫描任务 #${task.id} 已启动`);
          Router.push(`/scans/${task.id}/progress`);
        } catch (e) {
          Store.error('启动失败: ' + e.message);
        }
      }

      function fmtDate(s) {
        return s ? new Date(s).toLocaleString('zh-CN', { hour12: false }) : '-';
      }

      return () => {
        if (loading.value) {
          return h('div', { class: 'flex justify-center py-20' }, h('div', { class: 'loader' }));
        }
        if (!project.value) {
          return h('div', { class: 'max-w-4xl mx-auto py-12 text-center text-app-muted' }, '项目不存在');
        }

        const p = project.value;
        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          // 返回
          h('a', { class: 'text-app-muted hover:text-primary text-sm cursor-pointer', onClick: () => Router.push('/') }, '← 返回项目列表'),

          // 头部
          h('div', { class: 'card p-6 my-4' }, [
            h('div', { class: 'flex justify-between items-start' }, [
              h('div', null, [
                h('h1', { class: 'text-3xl font-bold mb-1' }, p.name),
                h('p', { class: 'text-app-muted' }, p.description || '— 暂无描述 —'),
                h('div', { class: 'flex gap-3 mt-3 text-sm' }, [
                  h('span', { class: 'badge badge-default' }, p.language),
                  h('span', { class: 'text-app-dim' }, `创建于 ${fmtDate(p.created_at)}`),
                ]),
              ]),
              h('div', { class: 'flex gap-2' }, [
                h('button', {
                  class: 'btn btn-primary',
                  onClick: () => Router.push(`/projects/${p.id}/upload`)
                }, '⬆ 上传新版本'),
              ]),
            ]),
          ]),

          // 版本列表
          h('h2', { class: 'text-xl font-semibold mb-4 mt-8' }, [
            '版本与扫描记录',
            h('span', { class: 'text-app-dim text-sm font-normal ml-2' }, `（共 ${versions.value.length} 个版本）`),
          ]),
          versions.value.length === 0
            ? h('div', { class: 'card p-10 text-center text-app-muted' }, [
                h('div', { class: 'text-3xl mb-3' }, '📦'),
                h('div', { class: 'mb-3' }, '还没有上传任何版本'),
                h('button', {
                  class: 'btn btn-primary',
                  onClick: () => Router.push(`/projects/${p.id}/upload`)
                }, '上传代码包'),
              ])
            : h('div', { class: 'space-y-4' },
                versions.value.map(v => {
                  const scans = scansByVersion.value[v.id] || [];
                  const latest = scans[0];
                  return h('div', { class: 'card p-5' }, [
                    h('div', { class: 'flex justify-between items-start' }, [
                      h('div', null, [
                        h('div', { class: 'flex items-center gap-3 mb-1' }, [
                          h('span', { class: 'text-lg font-semibold text-mono' }, v.version_tag),
                          latest && latest.grade && h(GradeBadge, { grade: latest.grade }),
                        ]),
                        h('div', { class: 'text-app-muted text-sm' },
                          `${v.total_files} 文件 · ${v.total_lines} 行 · 上传于 ${fmtDate(v.uploaded_at)}`),
                      ]),
                      h('div', { class: 'flex gap-2' }, [
                        h('button', {
                          class: 'btn btn-primary btn-sm',
                          onClick: () => startScan(v.id),
                        }, '🚀 启动扫描'),
                        latest && latest.status === 'done' && h('button', {
                          class: 'btn btn-ghost btn-sm',
                          onClick: () => Router.push(`/scans/${latest.id}`)
                        }, '查看结果'),
                      ]),
                    ]),
                    scans.length > 0 && h('div', { class: 'mt-4 pt-4 border-t border-app' }, [
                      h('div', { class: 'text-app-dim text-xs uppercase tracking-wider mb-2' },
                        `扫描历史（${scans.length}）`),
                      h('div', { class: 'space-y-2' },
                        scans.slice(0, 5).map(s =>
                          h('div', {
                            class: 'flex justify-between items-center text-sm hover:bg-card-3 px-2 py-1 rounded cursor-pointer',
                            onClick: () => Router.push(s.status === 'running' || s.status === 'pending'
                              ? `/scans/${s.id}/progress` : `/scans/${s.id}`),
                          }, [
                            h('div', { class: 'flex items-center gap-3' }, [
                              h('span', { class: 'text-app-muted text-mono' }, `#${s.id}`),
                              h('span', { class: `badge badge-${
                                s.status === 'done' ? 'success' :
                                s.status === 'failed' ? 'error' :
                                s.status === 'running' ? 'info' : 'default'
                              }` }, s.status),
                              h('span', { class: 'text-app-dim text-xs' }, fmtDate(s.created_at)),
                            ]),
                            h('div', { class: 'flex items-center gap-3' }, [
                              s.status === 'done' && h('span', { class: 'text-primary font-semibold' },
                                `${s.overall_score.toFixed(1)} 分`),
                              s.status === 'done' && h('span', { class: 'text-app-muted text-xs' },
                                `${s.total_issues} 问题`),
                            ]),
                          ])
                        )
                      ),
                    ]),
                  ]);
                })
              )
        ]);
      };
    },
  });
})();
