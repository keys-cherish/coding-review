import { routes } from '../router';

// ---- Icons (Lucide stroke-style SVG，内嵌以避免外部依赖) ----

const icons: Record<string, string> = {
    home:       '<path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1V9.5Z"/>',
    projects:   '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
    scan:       '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    radar:      '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="currentColor"/><path d="M12 3v18M3 12h18"/>',
    refactor:   '<path d="M14.7 6.3a4 4 0 0 0-5 5L4 17v3h3l5.7-5.7a4 4 0 0 0 5-5l-3 3-3-3 3-3Z"/><path d="M7 17l-3 3"/>',
    graph:      '<circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="18" r="2"/><path d="M6.5 7.5l4.5 9M17.5 7.5l-4.5 9"/>',
    flame:      '<path d="M12 2s5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4.5C10 6 12 2 12 2Z"/><path d="M12 14a2 2 0 0 0 2-2"/>',
    tree:       '<rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="5" rx="1"/><rect x="13" y="10" width="8" height="11" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/>',
    uml:        '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><path d="M10 6.5h4M10 17.5h4M6.5 10v4M17.5 10v4"/>',
    er:         '<rect x="3" y="4" width="8" height="6" rx="1"/><rect x="13" y="4" width="8" height="6" rx="1"/><rect x="3" y="14" width="8" height="6" rx="1"/><rect x="13" y="14" width="8" height="6" rx="1"/><path d="M11 7h2M11 17h2M7 10v4M17 10v4"/>',
    rules:      '<path d="M12 3v18M6 6v12M18 6v12"/><path d="M3 8h2M3 16h2M19 8h2M19 16h2"/>',
    report:     '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z"/><path d="M14 3v5h5"/>',
    settings:   '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    plus:       '<path d="M12 5v14M5 12h14"/>',
    shield:     '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
    search:     '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
};

function icon(name: string, cls = 'icon'): string {
    const body = icons[name] || '';
    return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
}

// ---- 导航分组 ----

interface NavGroup {
    title: string;
    items: { id: string; label: string; icon: string; badge?: string }[];
}

const navGroups: NavGroup[] = [
    {
        title: '工作台',
        items: [
            { id: 'home',     label: '概览',       icon: 'home' },
            { id: 'projects', label: '项目大厅',   icon: 'projects' },
            { id: 'scans',    label: '扫描历史',   icon: 'scan' },
        ],
    },
    {
        title: '架构分析',
        items: [
            { id: 'radar',    label: '架构雷达',   icon: 'radar',  badge: '6D' },
            { id: 'refactor', label: '重构建议',   icon: 'refactor', badge: 'NEW' },
            { id: 'graph',    label: '依赖图',     icon: 'graph' },
            { id: 'flame',    label: '火焰图',     icon: 'flame' },
            { id: 'treemap',  label: '热力 Treemap', icon: 'tree' },
        ],
    },
    {
        title: '工程视图',
        items: [
            { id: 'uml',      label: 'UML 工作台', icon: 'uml' },
            { id: 'er',       label: 'ER 图',      icon: 'er' },
        ],
    },
    {
        title: '配置',
        items: [
            { id: 'rules',    label: '规则配置',   icon: 'rules' },
            { id: 'reports',  label: '报告中心',   icon: 'report' },
            { id: 'settings', label: '设置',       icon: 'settings' },
        ],
    },
];

// ---- 布局挂载 ----

export function mountLayout(root: HTMLElement): void {
    root.innerHTML = `
        <div class="app-layout">
            <aside class="sidebar" id="sidebar">
                <div class="sidebar-header">
                    <div class="logo-mark">${icon('shield', '')}</div>
                    <div class="logo-text"><em>Code</em>Guard</div>
                </div>

                ${navGroups.map(g => `
                    <div class="sidebar-section">
                        <div class="sidebar-section-title">${g.title}</div>
                        ${g.items.map(it => `
                            <a class="sidebar-link" data-route="${it.id}" role="button" tabindex="0">
                                ${icon(it.icon)}
                                <span>${it.label}</span>
                                ${it.badge ? `<span class="badge">${it.badge}</span>` : ''}
                            </a>
                        `).join('')}
                    </div>
                `).join('')}

                <div class="sidebar-footer">
                    <div class="sidebar-user">
                        <div class="avatar">W</div>
                        <div class="user-info">
                            <div class="user-name">Developer</div>
                            <div class="user-role">Pro v1.0</div>
                        </div>
                    </div>
                </div>
            </aside>

            <div class="app-main">
                <header class="topbar" id="topbar">
                    <div class="topbar-left">
                        <div class="breadcrumb" id="breadcrumb"></div>
                    </div>
                    <div class="topbar-right">
                        <div class="search-box">
                            ${icon('search')}
                            <input type="text" placeholder="搜索项目、规则、问题..." aria-label="全局搜索">
                            <kbd>⌘K</kbd>
                        </div>
                        <button class="btn btn-ghost btn-icon btn-sm" title="通知">
                            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2">
                                <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>
                                <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>
                            </svg>
                        </button>
                    </div>
                </header>

                <div id="view-root"></div>
            </div>

            <!-- Toast 容器 -->
            <div class="toast-container" id="toast-container"></div>
        </div>
    `;

    // 给侧边栏链接挂键盘支持
    root.querySelectorAll<HTMLElement>('.sidebar-link').forEach(el => {
        el.addEventListener('click', () => {
            const target = el.dataset.route!;
            window.dispatchEvent(new CustomEvent('route:change', { detail: { id: target } }));
        });
        el.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                (el as HTMLElement).click();
            }
        });
    });
}

export function setActiveNav(routeId: string): void {
    document.querySelectorAll('.sidebar-link').forEach(el => {
        const isActive = (el as HTMLElement).dataset.route === routeId;
        el.classList.toggle('active', isActive);
    });

    // breadcrumb
    const def = routes.find(r => r.id === routeId);
    const bc = document.getElementById('breadcrumb');
    if (bc && def) {
        bc.innerHTML = `
            <span class="breadcrumb-item">CodeGuard</span>
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-item current">${def.title}</span>
        `;
    }
}
