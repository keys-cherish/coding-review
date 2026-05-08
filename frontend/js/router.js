/**
 * router.js - 极简 hash 路由
 *
 * 路由表是一个数组：[{ pattern: /^\/projects\/(\d+)$/, name: 'project-detail', component: 'ProjectDetailPage' }, ...]
 * 通过 reactive 暴露 currentRoute 给 App 组件。
 */
window.Router = (() => {
  const { reactive } = Vue;

  const routes = [
    { path: '/',                          name: 'home',           component: 'HomePage' },
    { path: '/projects/:id',              name: 'project',        component: 'ProjectDetailPage' },
    { path: '/projects/:id/upload',       name: 'upload',         component: 'UploadPage' },
    { path: '/scans/:id/progress',        name: 'scan-progress',  component: 'ScanProgressPage' },
    { path: '/scans/:id',                 name: 'scan-result',    component: 'ScanResultPage' },
    { path: '/scans/:id/issues',          name: 'issues',         component: 'IssuesPage' },
    { path: '/scans/:id/duplications',    name: 'duplications',   component: 'DuplicationsPage' },
    { path: '/scans/:id/complexity',      name: 'complexity',     component: 'ComplexityPage' },
    { path: '/scans/:id/report',          name: 'report',         component: 'ReportPage' },
    { path: '/rules',                     name: 'rules',          component: 'RulesPage' },
    { path: '/about',                     name: 'about',          component: 'AboutPage' },
  ];

  function compile(path) {
    const keys = [];
    const re = path.replace(/:[a-zA-Z_]+/g, (m) => {
      keys.push(m.slice(1));
      return '(\\d+|\\w+)';
    });
    return { regex: new RegExp('^' + re + '$'), keys };
  }
  routes.forEach(r => {
    const c = compile(r.path);
    r.regex = c.regex;
    r.keys = c.keys;
  });

  const state = reactive({
    name: 'home',
    component: 'HomePage',
    params: {},
    query: {},
    fullPath: '/',
  });

  function parseHash() {
    const hash = location.hash.replace(/^#/, '') || '/';
    const [pathPart, queryPart] = hash.split('?');
    const query = {};
    if (queryPart) {
      for (const pair of queryPart.split('&')) {
        const [k, v] = pair.split('=');
        query[decodeURIComponent(k)] = decodeURIComponent(v || '');
      }
    }
    for (const r of routes) {
      const m = r.regex.exec(pathPart);
      if (m) {
        const params = {};
        r.keys.forEach((k, i) => params[k] = m[i + 1]);
        state.name = r.name;
        state.component = r.component;
        state.params = params;
        state.query = query;
        state.fullPath = hash;
        return;
      }
    }
    // fallback
    state.name = 'home';
    state.component = 'HomePage';
    state.params = {};
    state.query = {};
    state.fullPath = '/';
  }

  function push(path) {
    if (location.hash !== '#' + path) {
      location.hash = '#' + path;
    } else {
      // 强制触发
      parseHash();
    }
  }

  window.addEventListener('hashchange', parseHash);
  parseHash();

  return { state, push, routes };
})();
