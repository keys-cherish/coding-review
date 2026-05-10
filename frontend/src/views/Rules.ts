import { pageShell, skeleton, emptyState } from '../components/PageShell';
import { toast } from '../components/Toast';
import { ruleApi, type Rule } from '../api';

let rulesCache: Rule[] = [];
let stats = { total: 0, enabled: 0, disabled: 0 };

export async function renderRulesPage(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '规则配置',
        subtitle: '40+ 内置规则，按需开启/关闭，支持按语言、严重度、类别过滤',
        actions: `
            <div class="stat-pill">
                <span class="dot dot-success"></span>
                <span id="rule-enabled-count">—</span> 已启用 / <span id="rule-total-count">—</span> 总计
            </div>
        `,
        body: `
            <div class="toolbar">
                <div class="input-group">
                    <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
                    <input class="input" id="r-search" placeholder="搜索规则代码、名称..." autocomplete="off">
                </div>
                <select class="select" id="r-lang">
                    <option value="">全部语言</option>
                    <option value="python">Python</option>
                    <option value="java">Java</option>
                </select>
                <select class="select" id="r-sev">
                    <option value="">全部级别</option>
                    <option value="error">高危</option>
                    <option value="warning">中危</option>
                    <option value="info">低危</option>
                </select>
                <select class="select" id="r-cat">
                    <option value="">全部类别</option>
                    <option value="naming">命名</option>
                    <option value="format">格式</option>
                    <option value="comment">注释</option>
                    <option value="complexity">复杂度</option>
                    <option value="import">导入</option>
                    <option value="dead_code">死代码</option>
                </select>
                <div class="toolbar-right">
                    <button class="btn btn-ghost btn-sm" id="r-enable-all">全部启用</button>
                    <button class="btn btn-ghost btn-sm" id="r-disable-all">全部禁用</button>
                </div>
            </div>
            <div class="card">
                <div id="rules-body">${skeleton(6)}</div>
            </div>
        `,
    });

    await loadRules(container);

    container.querySelector('#r-search')?.addEventListener('input', () => renderRules(container));
    container.querySelector('#r-lang')?.addEventListener('change', () => renderRules(container));
    container.querySelector('#r-sev')?.addEventListener('change', () => renderRules(container));
    container.querySelector('#r-cat')?.addEventListener('change', () => renderRules(container));
    container.querySelector('#r-enable-all')?.addEventListener('click', () => bulkToggle(container, true));
    container.querySelector('#r-disable-all')?.addEventListener('click', () => bulkToggle(container, false));
}

async function loadRules(container: HTMLElement): Promise<void> {
    const [rulesRes, statsRes] = await Promise.all([ruleApi.list(), ruleApi.stats()]);
    if (rulesRes.error) {
        toast.error({ title: '加载失败', message: rulesRes.error });
        (container.querySelector('#rules-body') as HTMLElement).innerHTML = emptyState({
            title: '无法加载规则', desc: rulesRes.error,
        });
        return;
    }
    rulesCache = rulesRes.data || [];
    if (statsRes.data) stats = statsRes.data;
    updateStats(container);
    renderRules(container);
}

function updateStats(container: HTMLElement): void {
    (container.querySelector('#rule-enabled-count') as HTMLElement).textContent = String(stats.enabled);
    (container.querySelector('#rule-total-count') as HTMLElement).textContent = String(stats.total);
}

function renderRules(container: HTMLElement): void {
    const q = (container.querySelector('#r-search') as HTMLInputElement).value.toLowerCase().trim();
    const lang = (container.querySelector('#r-lang') as HTMLSelectElement).value;
    const sev = (container.querySelector('#r-sev') as HTMLSelectElement).value;
    const cat = (container.querySelector('#r-cat') as HTMLSelectElement).value;

    const filtered = rulesCache.filter(r => {
        if (lang && r.language !== lang) return false;
        if (sev && r.severity !== sev) return false;
        if (cat && r.category !== cat) return false;
        if (q && !r.code.toLowerCase().includes(q) && !r.name.toLowerCase().includes(q)) return false;
        return true;
    });

    const body = container.querySelector('#rules-body') as HTMLElement;
    if (filtered.length === 0) {
        body.innerHTML = emptyState({ title: '没有匹配规则', desc: '尝试放宽筛选条件' });
        return;
    }

    body.innerHTML = `
        <table class="table">
            <thead>
                <tr>
                    <th style="width:140px">代码</th>
                    <th>名称</th>
                    <th style="width:100px">语言</th>
                    <th style="width:100px">类别</th>
                    <th style="width:90px">级别</th>
                    <th style="width:80px" class="text-right">启用</th>
                </tr>
            </thead>
            <tbody>
                ${filtered.map(r => `
                    <tr data-code="${r.code}">
                        <td><code class="code-chip">${r.code}</code></td>
                        <td>
                            <div class="cell-main">${escapeHtml(r.name)}</div>
                            ${r.description ? `<div class="cell-sub">${escapeHtml(r.description)}</div>` : ''}
                        </td>
                        <td><span class="badge badge-lang-${r.language}">${r.language.toUpperCase()}</span></td>
                        <td><span class="badge badge-subtle">${r.category}</span></td>
                        <td>${severityBadge(r.severity)}</td>
                        <td class="text-right">
                            <label class="switch">
                                <input type="checkbox" data-code="${r.code}" ${r.enabled ? 'checked' : ''}>
                                <span class="switch-track"></span>
                            </label>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    body.querySelectorAll<HTMLInputElement>('input[type=checkbox]').forEach(cb => {
        cb.addEventListener('change', async () => {
            const code = cb.dataset.code!;
            cb.disabled = true;
            const res = await ruleApi.toggle(code, cb.checked);
            cb.disabled = false;
            if (res.error) {
                cb.checked = !cb.checked;
                toast.error(res.error);
                return;
            }
            const rule = rulesCache.find(r => r.code === code);
            if (rule) {
                if (rule.enabled !== cb.checked) {
                    stats.enabled += cb.checked ? 1 : -1;
                    stats.disabled -= cb.checked ? 1 : -1;
                    rule.enabled = cb.checked;
                    updateStats(container);
                }
            }
            toast.success(`${code} 已${cb.checked ? '启用' : '禁用'}`);
        });
    });
}

async function bulkToggle(container: HTMLElement, enable: boolean): Promise<void> {
    if (!confirm(`确定要${enable ? '启用' : '禁用'}所有可见规则？`)) return;
    const body = container.querySelector('#rules-body') as HTMLElement;
    const boxes = Array.from(body.querySelectorAll<HTMLInputElement>('input[type=checkbox]'));
    const targets = boxes.filter(b => b.checked !== enable);
    if (targets.length === 0) { toast.info('无需变更'); return; }

    toast.info(`正在${enable ? '启用' : '禁用'} ${targets.length} 条规则...`);
    let ok = 0, fail = 0;
    for (const cb of targets) {
        const code = cb.dataset.code!;
        const res = await ruleApi.toggle(code, enable);
        if (res.error) fail++;
        else {
            ok++;
            cb.checked = enable;
            const rule = rulesCache.find(r => r.code === code);
            if (rule) rule.enabled = enable;
        }
    }
    stats.enabled = rulesCache.filter(r => r.enabled).length;
    stats.disabled = stats.total - stats.enabled;
    updateStats(container);
    toast.success(`${enable ? '启用' : '禁用'}完成：成功 ${ok}，失败 ${fail}`);
}

function severityBadge(sev: string): string {
    const map: Record<string, { cls: string; text: string }> = {
        error:   { cls: 'badge-danger',  text: '高危' },
        warning: { cls: 'badge-warning', text: '中危' },
        info:    { cls: 'badge-info',    text: '低危' },
    };
    const m = map[sev] || { cls: 'badge-subtle', text: sev };
    return `<span class="badge ${m.cls}">${m.text}</span>`;
}

function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]!));
}
