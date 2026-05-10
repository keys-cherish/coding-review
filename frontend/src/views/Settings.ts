import { pageShell } from '../components/PageShell';
import { systemApi } from '../api';
import { toast } from '../components/Toast';

export async function renderSettings(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '系统设置',
        subtitle: '查看服务状态、版本、语言支持与评分权重',
        body: `
            <div class="card">
                <div class="card-header">
                    <div class="card-title">基本信息</div>
                </div>
                <div class="card-body">
                    <div class="info-grid" id="info-grid">
                        <div class="info-row"><div class="info-k">应用名称</div><div class="info-v" id="info-name">—</div></div>
                        <div class="info-row"><div class="info-k">版本</div><div class="info-v" id="info-version">—</div></div>
                        <div class="info-row"><div class="info-k">描述</div><div class="info-v" id="info-desc">—</div></div>
                        <div class="info-row"><div class="info-k">支持语言</div><div class="info-v" id="info-langs">—</div></div>
                        <div class="info-row"><div class="info-k">扫描并发</div><div class="info-v" id="info-concurrency">—</div></div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">评分权重</div>
                    <div class="card-subtitle">规范度 / 重复度 / 复杂度 三维加权</div>
                </div>
                <div class="card-body" id="weights-body">
                    <div class="weight-row">
                        <span class="weight-label">规范度</span>
                        <div class="weight-bar"><div class="weight-fill" id="w-spec" style="width:0%"></div></div>
                        <span class="weight-value" id="w-spec-v">—</span>
                    </div>
                    <div class="weight-row">
                        <span class="weight-label">重复度</span>
                        <div class="weight-bar"><div class="weight-fill" id="w-dup" style="width:0%"></div></div>
                        <span class="weight-value" id="w-dup-v">—</span>
                    </div>
                    <div class="weight-row">
                        <span class="weight-label">复杂度</span>
                        <div class="weight-bar"><div class="weight-fill" id="w-cx" style="width:0%"></div></div>
                        <span class="weight-value" id="w-cx-v">—</span>
                    </div>
                </div>
            </div>
        `,
    });

    const res = await systemApi.info();
    if (res.error) {
        toast.error({ title: '无法加载系统信息', message: res.error });
        return;
    }
    const info = res.data!;
    const $ = (s: string) => container.querySelector(s) as HTMLElement;
    $('#info-name').textContent = info.name;
    $('#info-version').textContent = info.version;
    $('#info-desc').textContent = info.description;
    $('#info-langs').innerHTML = info.supported_languages.map(l => `<span class="badge badge-subtle">${l}</span>`).join(' ');
    $('#info-concurrency').textContent = String(info.scan_concurrency);

    const w = info.score_weights;
    $('#w-spec').style.width = `${w.spec * 100}%`;
    $('#w-dup').style.width = `${w.duplication * 100}%`;
    $('#w-cx').style.width = `${w.complexity * 100}%`;
    $('#w-spec-v').textContent = `${(w.spec * 100).toFixed(0)}%`;
    $('#w-dup-v').textContent = `${(w.duplication * 100).toFixed(0)}%`;
    $('#w-cx-v').textContent = `${(w.complexity * 100).toFixed(0)}%`;
}
