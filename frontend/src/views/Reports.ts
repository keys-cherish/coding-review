/**
 * 报告中心：选 scan，生成 + 下载 + 在线查看 报告。
 */
import { pageShell, emptyState } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';
import { reportApi } from '../api';

interface ReportRow {
    id: number;
    scan_task_id: number;
    format: string;
    file_path: string;
    generated_at: string;
}

export async function renderReports(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '报告中心',
        subtitle: '为扫描任务生成 HTML / Markdown 报告，支持一键下载',
        body: `
            <div class="viz-toolbar" id="rep-toolbar"></div>

            <div class="card" style="margin-top:16px">
                <div class="card-header">
                    <div class="card-title">生成报告</div>
                    <div class="card-actions">
                        <button class="btn btn-sm btn-primary" data-fmt="md">Markdown</button>
                        <button class="btn btn-sm btn-primary" data-fmt="html">HTML</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="card-subtitle">已生成的报告会出现在下方列表，点击即可下载。</div>
                </div>
            </div>

            <div class="card" style="margin-top:16px">
                <div class="card-header"><div class="card-title">历史报告</div></div>
                <div class="card-body" id="rep-list"></div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#rep-toolbar') as HTMLElement;
    let scanId: number | null = null;

    const refresh = async () => {
        if (!scanId) return;
        const list = container.querySelector('#rep-list') as HTMLElement;
        list.innerHTML = `<div class="empty-sm">加载中...</div>`;
        const { data, error } = await reportApi.list(scanId) as { data: ReportRow[] | null; error: string | null };
        if (error || !data) {
            list.innerHTML = emptyState({ title: '加载失败', desc: error || '' });
            return;
        }
        if (!data.length) {
            list.innerHTML = emptyState({ title: '暂无报告', desc: '点击上方按钮生成' });
            return;
        }
        list.innerHTML = `
            <table class="data-table">
                <thead><tr><th>#</th><th>格式</th><th>生成时间</th><th>路径</th><th style="width:180px"></th></tr></thead>
                <tbody>
                    ${data.map(r => `
                        <tr>
                            <td>${r.id}</td>
                            <td><span class="pill pill-info">${r.format.toUpperCase()}</span></td>
                            <td>${new Date(r.generated_at).toLocaleString('zh-CN', { hour12: false })}</td>
                            <td class="ellipsis" title="${escapeHtml(r.file_path)}">${escapeHtml(r.file_path.split(/[\\\\/]/).slice(-1)[0])}</td>
                            <td>
                                <a class="btn btn-sm btn-ghost" href="/api/reports/${r.id}/inline" target="_blank">查看</a>
                                <a class="btn btn-sm btn-primary" href="/api/reports/${r.id}/download">下载</a>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    };

    container.querySelectorAll('button[data-fmt]').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (!scanId) { toast.warning('请先选择扫描'); return; }
            const fmt = (btn as HTMLElement).dataset.fmt as 'md' | 'html';
            toast.info('正在生成报告...');
            const { data, error } = await reportApi.generate(scanId, fmt);
            if (error || !data) { toast.error(error || '生成失败'); return; }
            toast.success(`${fmt.toUpperCase()} 报告已生成`);
            refresh();
        });
    });

    await mountScanPicker(toolbar, (id) => { scanId = id; refresh(); });
}

function escapeHtml(s: string): string {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
}
