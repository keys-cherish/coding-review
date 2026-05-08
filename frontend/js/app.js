/**
 * app.js - Vue 应用主入口
 *
 * 包含：
 * - 顶部导航栏（Logo + 菜单 + 信息）
 * - 路由出口（动态切换页面）
 * - 全局 Toast 容器
 */
(function () {
  const { defineComponent, computed, onMounted, h, Transition } = Vue;

  const App = defineComponent({
    setup() {
      const route = computed(() => Router.state);

      onMounted(async () => {
        try {
          Store.state.appInfo = await API.info();
        } catch {
          Store.state.appInfo = { name: 'CodeGuard Pro', version: '1.0.0' };
        }
      });

      function isActive(name) {
        if (name === 'home') return route.value.name === 'home';
        return route.value.name === name || route.value.fullPath.startsWith('/' + name);
      }

      function navItem(label, path, name, icon) {
        return h('a', {
          href: '#' + path,
          class: 'nav-link ' + (isActive(name) ? 'active' : ''),
        }, [
          icon && h('span', { class: 'mr-1' }, icon),
          label,
        ]);
      }

      return () => {
        const comp = window[route.value.component];

        return h('div', { class: 'min-h-screen flex flex-col' }, [
          h('header', { class: 'topbar' }, [
            h('div', { class: 'max-w-7xl mx-auto px-6 h-16 flex items-center gap-6' }, [
              h('a', {
                href: '#/',
                class: 'flex items-center gap-3 hover:opacity-90',
              }, [
                h('span', { class: 'logo-mark' }, '⌘'),
                h('div', { class: 'flex flex-col leading-tight' }, [
                  h('span', { class: 'font-bold text-base' }, 'CodeGuard'),
                  h('span', { class: 'text-app-dim text-xs' }, 'Pro'),
                ]),
              ]),
              h('nav', { class: 'flex items-center gap-1 ml-6' }, [
                navItem('项目', '/', 'home'),
                navItem('规则库', '/rules', 'rules'),
                navItem('关于', '/about', 'about'),
              ]),
              h('div', { class: 'ml-auto text-xs text-app-dim font-mono' },
                Store.state.appInfo ?
                  'v' + Store.state.appInfo.version : '加载中...'),
            ]),
          ]),

          h('main', { class: 'flex-1' }, [
            comp
              ? h(Transition, { name: 'fade', mode: 'out-in' },
                  () => h(comp, { key: route.value.fullPath }))
              : h('div', { class: 'p-10 text-center text-app-muted' },
                  '页面 ' + route.value.component + ' 未注册'),
          ]),

          h('footer', { class: 'border-t border-app py-4 text-center text-app-dim text-xs' }, [
            'CodeGuard Pro · 智能代码质量管理与规范检测平台 · 软件工程课程作业',
          ]),

          h(ToastContainer),
        ]);
      };
    },
  });

  Vue.createApp(App).mount('#app');
})();
