/**
 * HomePage - 项目列表 + 概览
 *
 * 顶部 hero 区显示统计卡片，下方瀑布卡片为项目列表。
 */
window.HomePage = (() => {
  const { defineComponent, ref, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const projects = ref([]);
      const loading = ref(true);
      const showCreate = ref(false);
      const newProject = ref({ name: '', description: '', language: 'python' });
      const stats = ref(null);

      async function load() {
        loading.value = true;
        try {
          const [list, info] = await Promise.all([
            API.listProjects(),
            API.rulesStats().catch(() => null),
          ]);
          projects.value = list;
          stats.value = info;
        } catch (e) {
          Store.error('加载失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      async function createProject() {
        if (!newProject.value.name) {
          Store.error('请填写项目名');
          return;
        }
        try {
          const p = await API.createProject(newProject.value);
          Store.success(`项目 "${p.name}" 创建成功`);
          showCreate.value = false;
          newProject.value = { name: '', description: '', language: 'python' };
          load();
        } catch (e) {
          Store.error('创建失败: ' + e.message);
        }
      }

      async function removeProject(id) {
        if (!confirm('确认删除该项目？所有版本和扫描记录将被一并清除。')) return;
        try {
          await API.deleteProject(id);
          Store.success('已删除');
          load();
        } catch (e) {
          Store.error('删除失败: ' + e.message);
        }
      }

      function fmtDate(s) {
        if (!s) return '-';
        return new Date(s).toLocaleString('zh-CN', { hour12: false });
      }

      return () => {
        const summary = computeSummary(projects.value);
        return h('div', { class: 'max-w-7xl mx-auto px-6 py-10' }, [
          // Hero
          h('div', { class: 'mb-10' }, [
            h('h1', { class: 'text-4xl font-bold mb-3' }, [
              '欢迎使用 ',
              h('span', { class: 'score-big text-4xl', style: 'font-size: 2.25rem;' }, 'CodeGuard Pro'),
            ]),
            h('p', { class: 'text-app-muted text-lg max-w-3xl' },
              '上传你的代码包，三秒看清代码质量。规范、重复、复杂度三维评分一目了然，附带可执行的修改建议清单。'),
          ]),

          // 统计卡
          h('div', { class: 'grid grid-cols-1 md:grid-cols-4 gap-4 mb-8' }, [
            h(StatCard, { label: '项目总数', value: projects.value.length, color: 'primary' }),
            h(StatCard, { label: '已扫描版本', value: summary.scanned, color: 'success' }),
            h(StatCard, { label: '内置规则', value: stats.value ? stats.value.total : '-', hint: '可逐条启停', color: 'warning' }),
            h(StatCard, { label: '平均评分', value: summary.avgScore.toFixed(1), color: 'primary' }),
          ]),

          // Action bar
          h('div', { class: 'flex justify-between items-center mb-6' }, [
            h('h2', { class: 'text-xl font-semibold' }, '项目列表'),
            h('button', {
              class: 'btn btn-primary',
              onClick: () => { showCreate.value = !showCreate.value; }
            }, ['+ 新建项目']),
          ]),

          // 创建表单
          showCreate.value && h('div', { class: 'card p-5 mb-6' }, [
            h('h3', { class: 'text-lg font-semibold mb-4' }, '新建项目'),
            h('div', { class: 'grid grid-cols-1 md:grid-cols-3 gap-3 mb-3' }, [
              h('input', {
                class: 'input', placeholder: '项目名（必填）',
                value: newProject.value.name,
                onInput: (e) => newProject.value.name = e.target.value,
              }),
              h('input', {
                class: 'input md:col-span-2', placeholder: '简短描述（可选）',
                value: newProject.value.description,
                onInput: (e) => newProject.value.description = e.target.value,
              }),
            ]),
            h('div', { class: 'flex gap-3 items-center' }, [
              h('label', { class: 'text-app-muted text-sm' }, '主语言'),
              h('select', {
                class: 'input select w-40',
                value: newProject.value.language,
                onChange: (e) => newProject.value.language = e.target.value,
              }, [
                h('option', { value: 'python' }, 'Python'),
                h('option', { value: 'java' }, 'Java'),
                h('option', { value: 'multi' }, 'Python + Java'),
              ]),
              h('button', { class: 'btn btn-primary ml-auto', onClick: createProject }, '创建'),
              h('button', { class: 'btn btn-ghost', onClick: () => showCreate.value = false }, '取消'),
            ]),
          ]),

          // 列表
          loading.value
            ? h('div', { class: 'flex justify-center py-16' }, h('div', { class: 'loader' }))
            : projects.value.length === 0
              ? h('div', { class: 'card p-10 text-center text-app-muted' }, [
                  h('div', { class: 'text-3xl mb-2' }, '🗂'),
                  h('div', '还没有项目，点击右上角"新建项目"开始'),
                ])
              : h('div', { class: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' },
                  projects.value.map(p =>
                    h('div', {
                      class: 'card card-hover-lift p-5 cursor-pointer',
                      onClick: () => Router.push(`/projects/${p.id}`),
                    }, [
                      h('div', { class: 'flex justify-between items-start mb-3' }, [
                        h('div', null, [
                          h('div', { class: 'text-lg font-semibold mb-1' }, p.name),
                          h('div', { class: 'text-app-muted text-sm' },
                            p.description || '— 暂无描述 —'),
                        ]),
                        p.latest_grade && h(GradeBadge, { grade: p.latest_grade }),
                      ]),
                      h('div', { class: 'flex items-center justify-between text-xs text-app-muted mt-4 pt-3 border-t border-app' }, [
                        h('div', { class: 'flex gap-3' }, [
                          h('span', null, ['💻 ', langLabel(p.language)]),
                          h('span', null, [`📦 ${p.version_count || 0} 版本`]),
                          p.latest_score !== null && p.latest_score !== undefined &&
                            h('span', { class: 'text-primary font-semibold' }, [`⭐ ${p.latest_score.toFixed(1)}`]),
                        ]),
                        h('button', {
                          class: 'btn btn-sm btn-danger',
                          onClick: (e) => { e.stopPropagation(); removeProject(p.id); }
                        }, '删除'),
                      ]),
                      h('div', { class: 'text-app-dim text-xs mt-2' },
                        `创建于 ${fmtDate(p.created_at)}`),
                    ])
                  )
                )
        ]);
      };
    },
  });

  function computeSummary(projects) {
    const scored = projects.filter(p => p.latest_score !== null && p.latest_score !== undefined);
    const avg = scored.length === 0 ? 0 : scored.reduce((s, p) => s + p.latest_score, 0) / scored.length;
    return {
      scanned: scored.length,
      avgScore: avg,
    };
  }

  function langLabel(l) {
    return ({ python: 'Python', java: 'Java', multi: 'Python + Java' })[l] || l;
  }
})();
