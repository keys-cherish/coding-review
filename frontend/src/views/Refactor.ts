import { visApi, type RefactorPayload, type RefactorSuggestion } from '../api';
import { emptyState, pageShell } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';

const CATEGORY_LABELS: Record<string, string> = {
    method_decomp: '方法拆分',
    class_split: '类拆分',
    dep_cycle: '循环依赖',
    layer: '分层修正',
    dup: '重复抽取',
    arg_object: '参数对象',
    interface_split: '接口拆分',
};

const LEVEL_LABELS: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
};

export async function renderRefactor(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '重构建议',
        subtitle: '聚合复杂度、坏味道、重复代码、循环依赖与分层违规，生成可执行的重构任务清单',
        body: `
            <div class="viz-toolbar" id="refactor-toolbar"></div>

            <div class="refactor-layout" style="margin-top:16px">
                <div class="card refactor-main">
                    <div class="card-header">
                        <div>
                            <div class="card-title">优先级队列</div>
                            <div class="card-subtitle" id="refactor-count">请选择扫描任务</div>
                        </div>
                    </div>
                    <div class="card-body" id="refactor-list">
                        ${emptyState({ title: '等待选择扫描', desc: '选择一次已完成扫描后生成重构建议' })}
                    </div>
                </div>

                <div class="refactor-aside stack-v">
                    <div class="card">
                        <div class="card-header"><div class="card-title">建议分布</div></div>
                        <div class="card-body" id="refactor-categories"></div>
                    </div>

                    <div class="card">
                        <div class="card-header"><div class="card-title">执行策略</div></div>
                        <div class="card-body">
                            <div class="refactor-guide">
                                <div><b>1</b><span>优先处理高收益、低成本项，快速降低风险。</span></div>
                                <div><b>2</b><span>循环依赖和分层违规应先画边界，再逐步切断。</span></div>
                                <div><b>3</b><span>重复代码抽取后再拆复杂方法，避免重复返工。</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#refactor-toolbar') as HTMLElement;
    await mountScanPicker(toolbar, async (scanId) => {
        const list = container.querySelector('#refactor-list') as HTMLElement;
        const count = container.querySelector('#refactor-count') as HTMLElement;
        list.innerHTML = '<div class="empty-sm">正在生成重构建议...</div>';
        count.textContent = '分析中...';

        const { data, error } = await visApi.refactor(scanId);
        if (error || !data) {
            toast.error(error || '重构建议加载失败');
            count.textContent = '加载失败';
            list.innerHTML = emptyState({ title: '重构建议加载失败', desc: error || '请稍后重试' });
            return;
        }

        renderSummary(container, data);
        renderSuggestions(container, data.suggestions);
    });
}

function renderSummary(container: HTMLElement, data: RefactorPayload): void {
    const count = container.querySelector('#refactor-count') as HTMLElement;
    const categories = container.querySelector('#refactor-categories') as HTMLElement;
    count.innerHTML = data.total
        ? `共 <strong style="color:var(--brand)">${data.total}</strong> 条建议，已按优先级排序`
        : '当前扫描未发现需要聚合处理的重构项';

    const rows = Object.entries(data.by_category)
        .sort((a, b) => b[1] - a[1])
        .map(([category, value]) => `
            <div class="stat-row">
                <span class="stat-label">${escapeHtml(categoryLabel(category))}</span>
                <span class="stat-value">${value}</span>
            </div>
        `).join('');

    categories.innerHTML = rows || '<div class="empty-sm">暂无分类统计</div>';
}

function renderSuggestions(container: HTMLElement, suggestions: RefactorSuggestion[]): void {
    const list = container.querySelector('#refactor-list') as HTMLElement;
    if (!suggestions.length) {
        list.innerHTML = emptyState({
            title: '暂无重构建议',
            desc: '本次扫描未发现复杂度、重复、依赖或坏味道层面的聚合重构项',
        });
        return;
    }

    list.innerHTML = suggestions.map((item, index) => renderSuggestion(item, index)).join('');
}

function renderSuggestion(item: RefactorSuggestion, index: number): string {
    const priorityClass = item.priority >= 80 ? 'danger' : item.priority >= 50 ? 'warn' : 'info';
    const targets = item.targets.slice(0, 5).map(t => `<code>${escapeHtml(t)}</code>`).join('');
    const metrics = renderMetrics(item.metrics);

    return `
        <div class="refactor-item priority-${priorityClass}">
            <div class="refactor-rank">#${index + 1}</div>
            <div class="refactor-content">
                <div class="refactor-head">
                    <div>
                        <div class="refactor-title">${escapeHtml(item.title)}</div>
                        <div class="refactor-meta">
                            <span class="pill pill-info">${escapeHtml(categoryLabel(item.category))}</span>
                            <span class="pill pill-${impactPill(item.impact)}">收益 ${escapeHtml(levelLabel(item.impact))}</span>
                            <span class="pill pill-muted">成本 ${escapeHtml(levelLabel(item.effort))}</span>
                        </div>
                    </div>
                    <div class="refactor-priority">
                        <strong>${item.priority}</strong>
                        <span>Priority</span>
                    </div>
                </div>
                <div class="refactor-rationale">${escapeHtml(item.rationale)}</div>
                ${targets ? `<div class="refactor-targets">${targets}</div>` : ''}
                ${metrics ? `<div class="refactor-metrics">${metrics}</div>` : ''}
            </div>
        </div>
    `;
}

function renderMetrics(metrics: Record<string, unknown>): string {
    return Object.entries(metrics).slice(0, 6).map(([key, value]) => {
        const label = key.replace(/_/g, ' ');
        const text = typeof value === 'object' ? JSON.stringify(value) : String(value);
        return `<span><b>${escapeHtml(label)}</b> ${escapeHtml(text)}</span>`;
    }).join('');
}

function categoryLabel(category: string): string {
    return CATEGORY_LABELS[category] || category;
}

function levelLabel(level: string): string {
    return LEVEL_LABELS[level] || level;
}

function impactPill(impact: string): string {
    if (impact === 'high') return 'danger';
    if (impact === 'medium') return 'warn';
    return 'info';
}

function escapeHtml(s: string): string {
    return s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
}
