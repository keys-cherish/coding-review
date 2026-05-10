import { setActiveNav } from './components/Layout';
import { renderHome } from './views/Home';
import { renderProjects } from './views/Projects';
import { renderRulesPage } from './views/Rules';
import { renderScans } from './views/Scans';
import { renderRadar } from './views/Radar';
import { renderRefactor } from './views/Refactor';
import { renderGraph } from './views/Graph';
import { renderFlame } from './views/Flame';
import { renderTreemap } from './views/Treemap';
import { renderUML } from './views/UML';
import { renderER } from './views/ER';
import { renderReports } from './views/Reports';
import { renderSettings } from './views/Settings';

export interface RouteDef {
    id: string;
    title: string;
    render: (container: HTMLElement) => void | Promise<void>;
}

export const routes: RouteDef[] = [
    { id: 'home',     title: '概览',        render: renderHome },
    { id: 'projects', title: '项目大厅',    render: renderProjects },
    { id: 'scans',    title: '扫描历史',    render: renderScans },
    { id: 'radar',    title: '架构雷达',    render: renderRadar },
    { id: 'refactor', title: '重构建议',    render: renderRefactor },
    { id: 'graph',    title: '依赖图',      render: renderGraph },
    { id: 'flame',    title: '火焰图',      render: renderFlame },
    { id: 'treemap',  title: '热力 Treemap', render: renderTreemap },
    { id: 'uml',      title: 'UML 工作台',  render: renderUML },
    { id: 'er',       title: 'ER 图',       render: renderER },
    { id: 'rules',    title: '规则配置',    render: renderRulesPage },
    { id: 'reports',  title: '报告中心',    render: renderReports },
    { id: 'settings', title: '设置',        render: renderSettings },
];

class Router {
    private current = '';
    private root: HTMLElement | null = null;
    private cleanups: Array<() => void> = [];

    public start(_defs: RouteDef[]): void {
        this.root = document.getElementById('view-root');
        if (!this.root) throw new Error('#view-root not found');

        window.addEventListener('route:change', ((e: CustomEvent) => {
            this.navigate(e.detail.id);
        }) as EventListener);

        window.addEventListener('popstate', () => {
            const id = (location.hash || '#home').slice(1);
            this.navigate(id, false);
        });

        const initial = (location.hash || '#home').slice(1);
        this.navigate(initial, false);
    }

    public navigate(id: string, push = true): void {
        const def = routes.find(r => r.id === id);
        if (!def || !this.root) return;

        if (push) location.hash = id;
        this.current = id;
        this.cleanups.forEach(c => { try { c(); } catch {} });
        this.cleanups = [];

        this.root.innerHTML = `<div class="view" data-view="${id}"></div>`;
        const container = this.root.firstElementChild as HTMLElement;
        setActiveNav(id);

        try {
            const result = def.render(container);
            if (result && typeof (result as any).catch === 'function') {
                (result as Promise<void>).catch(err => console.error('view render error:', err));
            }
        } catch (err) {
            console.error('view render error:', err);
            container.innerHTML = `<div class="empty"><div class="empty-title">页面加载失败</div><div class="empty-desc">${err}</div></div>`;
        }
    }

    public addCleanup(fn: () => void): void {
        this.cleanups.push(fn);
    }

    public get currentId() { return this.current; }
}

export const router = new Router();
