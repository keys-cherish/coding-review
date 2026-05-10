/**
 * 通用的页面外壳 helper。
 * 保证所有页面标题/动作区/空状态风格一致。
 */

export interface PageShellOpt {
    title: string;
    subtitle?: string;
    actions?: string;        // 右上角 HTML 片段
    body: string;
}

export function pageShell(opt: PageShellOpt): string {
    return `
        <div class="page">
            <div class="page-header">
                <div>
                    <h1 class="page-title">${opt.title}</h1>
                    ${opt.subtitle ? `<p class="page-subtitle">${opt.subtitle}</p>` : ''}
                </div>
                ${opt.actions ? `<div class="page-actions">${opt.actions}</div>` : ''}
            </div>
            <div class="page-body">${opt.body}</div>
        </div>
    `;
}

export interface EmptyStateOpt {
    icon?: string;
    title: string;
    desc?: string;
    action?: string;
}

export function emptyState(opt: EmptyStateOpt): string {
    return `
        <div class="empty">
            ${opt.icon ? `<div class="empty-icon">${opt.icon}</div>` : ''}
            <div class="empty-title">${opt.title}</div>
            ${opt.desc ? `<div class="empty-desc">${opt.desc}</div>` : ''}
            ${opt.action ? `<div class="empty-action">${opt.action}</div>` : ''}
        </div>
    `;
}

export function skeleton(lines = 3): string {
    return `
        <div class="skeleton-block">
            ${Array.from({ length: lines }).map(() => '<div class="skeleton-line"></div>').join('')}
        </div>
    `;
}

export function comingSoon(title: string, desc: string): string {
    return pageShell({
        title,
        body: `
            <div class="empty">
                <div class="empty-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 6v6l4 2"/>
                    </svg>
                </div>
                <div class="empty-title">${title}</div>
                <div class="empty-desc">${desc}</div>
                <div class="empty-action">
                    <span class="badge badge-info">即将推出</span>
                </div>
            </div>
        `,
    });
}
