import { router } from '../router';
import { renderHome } from '../views/Home';
import { renderDashboard } from '../views/Dashboard';
import { renderRules } from '../views/Rules';

export function renderHeader(parent: HTMLElement) {
    const header = document.createElement('header');
    header.style.cssText = `
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 48px; background: rgba(252, 252, 251, 0.85);
    backdrop-filter: blur(12px); position: sticky; top: 0; z-index: 100;
    border-bottom: 1px solid rgba(0,0,0,0.05);
  `;

    header.innerHTML = `
    <div class="logo" style="font-size: 22px; font-weight: bold; display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 24px;">🛡️</span>
        <span style="font-family: Georgia, serif; color: var(--primary); font-style: italic;">Code</span>Guard
    </div>
    <nav class="nav-links" style="display: flex; gap: 36px; font-weight: 500; font-size: 15px;">
        <a data-target="home" class="active" style="cursor: pointer; color: var(--primary); border-bottom: 2px solid var(--primary);">首页介绍</a>
        <a data-target="dashboard" style="cursor: pointer; color: var(--text-light);">大盘监控</a>
        <a data-target="rules" style="cursor: pointer; color: var(--text-light);">规则配置</a>
    </nav>
    <div class="user-avatar" style="width: 36px; height: 36px; background: var(--primary-light); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--primary); font-weight: bold; border: 2px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer;">W</div>
  `;

    parent.appendChild(header);

    const links = header.querySelectorAll('.nav-links a');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            const target = (e.target as HTMLElement).getAttribute('data-target');

            links.forEach(l => {
                (l as HTMLElement).style.color = 'var(--text-light)';
                (l as HTMLElement).style.borderBottom = 'none';
            });
            (e.target as HTMLElement).style.color = 'var(--primary)';
            (e.target as HTMLElement).style.borderBottom = '2px solid var(--primary)';

            if (target === 'home') router.navigate(renderHome);
            if (target === 'dashboard') router.navigate(renderDashboard);
            if (target === 'rules') router.navigate(renderRules);
        });
    });
}
