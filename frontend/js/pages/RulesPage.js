/**
 * RulesPage - 规则启停管理
 *
 * 按语言（python / java）+ 类别分组展示，每条可单独启停。
 * 顶部统计：总数 / 启用 / 禁用 / 各类别分布。
 */
window.RulesPage = (() => {
  const { defineComponent, ref, computed, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const rules = ref([]);
      const stats = ref(null);
      const loading = ref(true);
      const filterLang = ref('');
      const filterCat = ref('');
      const keyword = ref('');

      async function load() {
        loading.value = true;
        try {
          const [list, st] = await Promise.all([
            API.listRules(filterLang.value || undefined),
            API.rulesStats(),
          ]);
          rules.value = list;
          stats.value = st;
        } catch (e) {
          Store.error('加载规则失败: ' + e.message);
        } finally {
          loading.value = false;
        }
      }
      onMounted(load);

      async function toggle(rule) {
        try {
          await API.toggleRule(rule.code, !rule.enabled);
          rule.enabled = !rule.enabled;
          Store.success(rule.code + (rule.enabled ? ' 已启用' : ' 已禁用'));
        } catch (e) {
          Store.error('切换失败: ' + e.message);
        }
      }

      const filtered = computed(() => {
        let list = rules.value;
        if (filterCat.value) list = list.filter(r => r.category === filterCat.value);
        if (keyword.value.trim()) {
          const k = keyword.value.toLowerCase();
          list = list.filter(r =>
            r.code.toLowerCase().includes(k) ||
            r.name.toLowerCase().includes(k) ||
            (r.description || '').toLowerCase().includes(k)
          );
        }
        return list;
      });

      const categories = computed(() => {
        const set = new Set(rules.value.map(r => r.category));
        return Array.from(set).sort();
      });

      const grouped = computed(() => {
        const map = {};
        for (const r of filtered.value) {
          const key = r.language + '·' + r.category;
          if (!map[key]) map[key] = { language: r.language, category: r.category, items: [] };
          map[key].items.push(r);
        }
        return Object.values(map).sort((a, b) =>
          (a.language + a.category).localeCompare(b.language + b.category));
      });

      function severityClass(s) {
        return ({ error: 'badge-error', warning: 'badge-warning', info: 'badge-info' })[s] || 'badge-info';
      }

      function langLabel(l) {
        return ({ python: 'Python', java: 'Java' })[l] || l;
      }

      function catLabel(c) {
        return ({
          naming: '命名', indent: '缩进', comment: '注释', spacing: '空格',
          magic_number: '魔法值', dead_code: '无效代码', complexity: '复杂度',
          line_length: '行长度', imports: '导入', javadoc: 'Javadoc',
        })[c] || c;
      }

      return () => {
        const list = filtered.value;
        const groups = grouped.value;
        const cats = categories.value;
        const st = stats.value || { total: 0, enabled: 0, disabled: 0 };

        return h('div', { class: 'max-w-7xl mx-auto px-6 py-8' }, [
          h('div', { class: 'flex items-center gap-3 mb-6' }, [
            h('button', { class: 'btn btn-ghost btn-sm', onClick: () => Router.push('/') }, '← 主页'),
            h('h1', { class: 'text-2xl font-bold' }, '规则管理'),
            h('div', { class: 'ml-auto text-app-muted text-sm' },
              '过滤后 ' + list.length + ' 条'),
          ]),

          h('div', { class: 'grid grid-cols-2 md:grid-cols-4 gap-3 mb-6' }, [
            h(StatCard, { label: '内置规则', value: st.total, color: 'primary' }),
            h(StatCard, { label: '已启用', value: st.enabled, color: 'success' }),
            h(StatCard, { label: '已禁用', value: st.disabled, color: 'warning' }),
            h(StatCard, { label: '类别', value: cats.length, color: 'primary' }),
          ]),

          h('div', { class: 'card p-4 mb-4' }, [
            h('div', { class: 'flex flex-wrap gap-3 items-center' }, [
              h('input', {
                class: 'input flex-1 min-w-48',
                placeholder: '搜索规则码 / 名称 / 描述',
                value: keyword.value,
                onInput: (e) => keyword.value = e.target.value,
              }),
              h('select', {
                class: 'input select w-40',
                value: filterLang.value,
                onChange: (e) => { filterLang.value = e.target.value; load(); },
              }, [
                h('option', { value: '' }, '全部语言'),
                h('option', { value: 'python' }, 'Python'),
                h('option', { value: 'java' }, 'Java'),
              ]),
              h('select', {
                class: 'input select w-40',
                value: filterCat.value,
                onChange: (e) => filterCat.value = e.target.value,
              }, [
                h('option', { value: '' }, '全部类别'),
                ...cats.map(c => h('option', { value: c }, catLabel(c))),
              ]),
            ]),
          ]),

          loading.value
            ? h('div', { class: 'flex justify-center py-16' }, h('div', { class: 'loader' }))
            : list.length === 0
              ? h('div', { class: 'card p-10 text-center text-app-muted' }, '没有匹配的规则')
              : h('div', { class: 'space-y-4' }, groups.map(g =>
                  h('div', { class: 'card overflow-hidden' }, [
                    h('div', { class: 'px-4 py-3 border-b border-app bg-app flex items-center gap-2' }, [
                      h('span', { class: 'badge badge-primary' }, langLabel(g.language)),
                      h('span', { class: 'text-sm font-semibold' }, catLabel(g.category)),
                      h('span', { class: 'text-app-dim text-xs ml-auto' }, g.items.length + ' 条'),
                    ]),
                    h('div', { class: 'divide-y divide-app' }, g.items.map(r =>
                      h('div', {
                        class: 'p-4 flex items-start gap-3 hover:bg-card-hover',
                        key: r.code,
                      }, [
                        h('div', { class: 'flex-1 min-w-0' }, [
                          h('div', { class: 'flex items-center gap-2 mb-1' }, [
                            h('span', { class: 'font-mono text-sm text-primary' }, r.code),
                            h('span', { class: 'badge ' + severityClass(r.severity) },
                              ({ error: '严重', warning: '警告', info: '提示' })[r.severity] || r.severity),
                          ]),
                          h('div', { class: 'text-sm font-semibold mb-1' }, r.name),
                          h('div', { class: 'text-app-muted text-xs' }, r.description || '—'),
                        ]),
                        h('label', { class: 'switch shrink-0' }, [
                          h('input', {
                            type: 'checkbox',
                            checked: r.enabled,
                            onChange: () => toggle(r),
                          }),
                          h('span', { class: 'slider' }),
                        ]),
                      ])
                    )),
                  ])
                )),
        ]);
      };
    },
  });
})();
