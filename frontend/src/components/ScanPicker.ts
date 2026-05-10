/**
 * 图表页通用 scan 选择器。
 *
 * 用法：
 *   const picker = await mountScanPicker(container, (scanId) => render(scanId));
 *   picker.setScan(42) 可外部触发切换
 */
import { visApi, type VizScan } from '../api';
import { toast } from './Toast';

export interface ScanPickerHandle {
    scans: VizScan[];
    currentScanId: number | null;
    setScan: (id: number) => void;
}

export async function mountScanPicker(
    toolbar: HTMLElement,
    onChange: (scanId: number, scan: VizScan) => void,
): Promise<ScanPickerHandle> {
    toolbar.innerHTML = `
        <label class="scan-picker">
            <span class="scan-picker-label">扫描快照</span>
            <select class="scan-picker-select" disabled>
                <option>加载中...</option>
            </select>
        </label>
        <span class="scan-picker-meta" id="scan-picker-meta"></span>
    `;
    const select = toolbar.querySelector('.scan-picker-select') as HTMLSelectElement;
    const meta = toolbar.querySelector('#scan-picker-meta') as HTMLElement;

    const { data, error } = await visApi.listScans();
    if (error || !data) {
        select.innerHTML = `<option>加载失败</option>`;
        toast.error(error || '扫描列表加载失败');
        return { scans: [], currentScanId: null, setScan: () => {} };
    }

    const done = data.filter(s => s.status === 'done');
    if (done.length === 0) {
        select.innerHTML = `<option>暂无已完成扫描</option>`;
        meta.textContent = '请先在「项目大厅」创建并完成一次扫描';
        return { scans: [], currentScanId: null, setScan: () => {} };
    }

    select.innerHTML = done.map(s => {
        const dt = s.created_at ? new Date(s.created_at).toLocaleString('zh-CN', { hour12: false }) : '';
        return `<option value="${s.id}">#${s.id} · ${escapeHtml(s.project_name)} · ${escapeHtml(s.version_tag)} · ${dt}</option>`;
    }).join('');
    select.disabled = false;

    const handle: ScanPickerHandle = {
        scans: done,
        currentScanId: done[0].id,
        setScan: (id: number) => {
            select.value = String(id);
            select.dispatchEvent(new Event('change'));
        },
    };

    const renderMeta = (scan: VizScan) => {
        const dup = (scan.duplication_rate * 100).toFixed(1);
        meta.innerHTML = `
            <span class="pill pill-${gradeColor(scan.grade)}">${scan.grade || '-'}</span>
            <span class="pill pill-muted">综合 ${scan.overall_score?.toFixed(1) ?? '-'}</span>
            <span class="pill pill-muted">问题 ${scan.total_issues}</span>
            <span class="pill pill-muted">重复率 ${dup}%</span>
        `;
    };

    select.addEventListener('change', () => {
        const id = Number(select.value);
        const scan = done.find(s => s.id === id);
        if (!scan) return;
        handle.currentScanId = id;
        renderMeta(scan);
        onChange(id, scan);
    });

    renderMeta(done[0]);
    onChange(done[0].id, done[0]);
    return handle;
}

function gradeColor(g: string | null): string {
    if (!g) return 'muted';
    if (g === 'A') return 'ok';
    if (g === 'B') return 'info';
    if (g === 'C') return 'warn';
    return 'danger';
}

function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
}
