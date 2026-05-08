/**
 * AboutPage - 关于
 *
 * 项目介绍、版本号、特性卡片、开发栈、链接。
 */
window.AboutPage = (() => {
  const { defineComponent, ref, onMounted, h } = Vue;

  return defineComponent({
    setup() {
      const info = ref(null);

      onMounted(async () => {
        try {
          info.value = await API.info();
        } catch {
          info.value = null;
        }
      });

      const features = [
        { icon: '🔍', title: '多语言扫描', desc: 'Python 与 Java 代码的命名 / 缩进 / 注释 / 魔法值等十余项规则检查' },
        { icon: '🧬', title: '重复代码检测', desc: '基于 token 序列与 AST 标准化的双重指纹算法，识别复制粘贴' },
        { icon: '⚡', title: '复杂度分析', desc: '同时计算 McCabe 圈复杂度与 Cognitive Complexity，精确定位高风险函数' },
        { icon: '⭐', title: '三维评分', desc: '规范度 / 重复度 / 复杂度三个维度加权综合，A/B/C/D 四级评定' },
        { icon: '📊', title: '可视化报告', desc: '雷达图 / 饼图 / 热力树状图多种图表，HTML / PDF / Markdown 三种导出' },
        { icon: '🚀', title: '实时进度', desc: 'WebSocket 推送扫描进度，大型项目可见即所得' },
      ];

      const stack = [
        { name: 'FastAPI', desc: '后端框架' },
        { name: 'SQLAlchemy 2.0', desc: 'ORM' },
        { name: 'Vue 3', desc: '前端框架' },
        { name: 'ECharts', desc: '可视化' },
        { name: 'Tailwind CSS', desc: '样式' },
        { name: 'Jinja2', desc: '报告模板' },
      ];

      return () => h('div', { class: 'max-w-5xl mx-auto px-6 py-10' }, [
        h('div', { class: 'mb-10 text-center' }, [
          h('h1', { class: 'text-4xl font-bold mb-3' }, [
            h('span', { class: 'score-big' }, 'CodeGuard Pro'),
          ]),
          h('p', { class: 'text-app-muted text-lg' },
            '智能代码质量管理与规范检测平台'),
          info.value && h('p', { class: 'text-app-dim text-sm mt-2' },
            'v' + info.value.version),
        ]),

        h('div', { class: 'card p-6 mb-6' }, [
          h('h2', { class: 'text-lg font-semibold mb-3' }, '项目背景'),
          h('p', { class: 'text-app-muted text-sm leading-relaxed' },
            '本系统以代码项目管理为基础，融合代码解析、规范扫描、重复率检测、复杂度分析、质量评分技术，构建完整代码质量管理平台。\n\n' +
            '面向高校《软件工程》课程实践场景设计，作业、课程项目、毕业设计皆可一键体检：上传 ZIP，秒级出分，附带可执行的修改建议清单。'),
        ]),

        h('h2', { class: 'text-xl font-semibold mb-4' }, '核心特性'),
        h('div', { class: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8' },
          features.map(f =>
            h('div', { class: 'card p-5' }, [
              h('div', { class: 'text-3xl mb-2' }, f.icon),
              h('div', { class: 'font-semibold mb-1' }, f.title),
              h('div', { class: 'text-app-muted text-xs' }, f.desc),
            ])
          )),

        h('h2', { class: 'text-xl font-semibold mb-4' }, '技术栈'),
        h('div', { class: 'card p-5 mb-8' }, [
          h('div', { class: 'flex flex-wrap gap-3' }, stack.map(s =>
            h('div', { class: 'badge badge-primary text-sm py-2 px-3' }, [
              h('span', { class: 'font-bold mr-2' }, s.name),
              h('span', { class: 'text-app-muted' }, s.desc),
            ])
          )),
        ]),

        info.value && h('div', { class: 'card p-5' }, [
          h('h2', { class: 'text-lg font-semibold mb-3' }, '运行参数'),
          h('div', { class: 'grid grid-cols-2 gap-3 text-sm' }, [
            h('div', null, [
              h('span', { class: 'text-app-muted' }, '支持语言：'),
              h('span', null, info.value.supported_languages.join(' / ')),
            ]),
            h('div', null, [
              h('span', { class: 'text-app-muted' }, '扫描并发度：'),
              h('span', null, info.value.scan_concurrency),
            ]),
            h('div', { class: 'col-span-2' }, [
              h('span', { class: 'text-app-muted' }, '评分权重：'),
              h('span', null,
                '规范度 ' + info.value.score_weights.spec +
                ' · 重复度 ' + info.value.score_weights.duplication +
                ' · 复杂度 ' + info.value.score_weights.complexity),
            ]),
          ]),
        ]),

        h('div', { class: 'text-center text-app-dim text-xs mt-10 pt-6 border-t border-app' }, [
          h('div', null, '© 2026 CodeGuard Pro · 软件工程实践课题 8 · 课程作业'),
          h('div', { class: 'mt-1' }, '由 FastAPI + Vue 3 驱动'),
        ]),
      ]);
    },
  });
})();
