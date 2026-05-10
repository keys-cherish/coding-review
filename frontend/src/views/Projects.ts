import { pageShell, emptyState, skeleton } from '../components/PageShell';
import { openModal, closeModal } from '../components/Modal';
import { toast } from '../components/Toast';
import { projectApi, scanApi, type Project } from '../api';
import { router } from '../router';

let projectsCache: Project[] = [];

export async function renderProjects(container: HTMLElement): Promise<void> {
    container.innerHTML = pageShell({
        title: '项目大厅',
        subtitle: '管理代码仓库，创建版本并触发扫描',
        actions: `
            <button class="btn btn-secondary btn-sm" id="btn-refresh">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 15.5-6.5L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.5L3 16"/><path d="M3 21v-5h5"/></svg>
                刷新
            </button>
            <button class="btn btn-primary btn-sm" id="btn-create">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
                新建项目
            </button>
        `,
        body: `
            <div class="toolbar">
                <div class="input-group">
                    <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
                    <input class="input" type="text" id="search" placeholder="搜索项目名称..." autocomplete="off">
                </div>
                <select class="select" id="filter-lang">
                    <option value="">所有语言</option>
                    <option value="python">Python</option>
                    <option value="java">Java</option>
                    <option value="multi">多语言</option>
                </select>
            </div>
            <div id="projects-list">${skeleton(4)}</div>
        `,
    });

    const refresh = () => loadProjects(container);
    container.querySelector('#btn-create')?.addEventListener('click', () => openCreateDialog(refresh));
    container.querySelector('#btn-refresh')?.addEventListener('click', refresh);
    container.querySelector('#search')?.addEventListener('input', () => renderList(container));
    container.querySelector('#filter-lang')?.addEventListener('change', () => renderList(container));

    await refresh();
}

async function loadProjects(container: HTMLElement): Promise<void> {
    const res = await projectApi.list();
    if (res.error) {
        toast.error({ title: '加载失败', message: res.error });
        const list = container.querySelector('#projects-list') as HTMLElement;
        list.innerHTML = emptyState({
            icon: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
            title: '无法连接到后端',
            desc: res.error,
            action: `<button class="btn btn-primary btn-sm" onclick="location.reload()">重试</button>`,
        });
        return;
    }
    projectsCache = res.data || [];
    renderList(container);
}

function renderList(container: HTMLElement): void {
    const searchEl = container.querySelector('#search') as HTMLInputElement;
    const langEl = container.querySelector('#filter-lang') as HTMLSelectElement;
    const q = searchEl?.value.toLowerCase().trim() || '';
    const lang = langEl?.value || '';

    const filtered = projectsCache.filter(p => {
        if (lang && p.language !== lang) return false;
        if (q && !p.name.toLowerCase().includes(q) && !(p.description || '').toLowerCase().includes(q)) return false;
        return true;
    });

    const list = container.querySelector('#projects-list') as HTMLElement;

    if (projectsCache.length === 0) {
        list.innerHTML = emptyState({
            icon: '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/></svg>',
            title: '还没有项目',
            desc: '创建第一个项目，上传代码开始扫描',
            action: `<button class="btn btn-primary btn-sm" id="empty-create">创建项目</button>`,
        });
        list.querySelector('#empty-create')?.addEventListener('click', () =>
            openCreateDialog(() => loadProjects(container))
        );
        return;
    }

    if (filtered.length === 0) {
        list.innerHTML = emptyState({
            title: '没有匹配的项目',
            desc: '尝试调整搜索关键字或筛选条件',
        });
        return;
    }

    list.innerHTML = `
        <div class="project-grid">
            ${filtered.map(p => projectCard(p)).join('')}
        </div>
    `;

    // 卡片事件
    list.querySelectorAll<HTMLElement>('.project-card').forEach(el => {
        const id = Number(el.dataset.id);

        el.querySelector('.btn-upload')?.addEventListener('click', (e) => {
            e.stopPropagation();
            openUploadDialog(id, () => loadProjects(container));
        });

        el.querySelector('.btn-del')?.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (!confirm(`确认删除项目？该操作不可恢复。`)) return;
            const resp = await projectApi.delete(id);
            if (resp.error) toast.error(resp.error);
            else {
                toast.success('项目已删除');
                loadProjects(container);
            }
        });

        el.addEventListener('click', () => {
            sessionStorage.setItem('cg:currentProjectId', String(id));
            router.navigate('scans');
        });
    });
}

function projectCard(p: Project): string {
    const grade = p.latest_grade || '—';
    const score = p.latest_score != null ? p.latest_score.toFixed(1) : '—';
    const gradeClass = p.latest_grade ? `grade-${p.latest_grade.toLowerCase()}` : 'grade-none';

    return `
        <article class="project-card" data-id="${p.id}">
            <header class="project-card-head">
                <div class="project-lang lang-${p.language}">${p.language.toUpperCase()}</div>
                <div class="project-actions">
                    <button class="btn btn-ghost btn-icon btn-sm btn-upload" title="上传代码">
                        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v14M6 9l6-6 6 6"/><path d="M4 21h16"/></svg>
                    </button>
                    <button class="btn btn-ghost btn-icon btn-sm btn-del" title="删除">
                        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6"/><path d="M5 7l1 13a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-13M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/></svg>
                    </button>
                </div>
            </header>
            <h3 class="project-name">${escapeHtml(p.name)}</h3>
            <p class="project-desc">${escapeHtml(p.description || '暂无描述')}</p>
            <footer class="project-card-foot">
                <div class="meta-item">
                    <span class="meta-label">版本数</span>
                    <span class="meta-value">${p.version_count}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">最新评分</span>
                    <span class="meta-value">${score}</span>
                </div>
                <div class="grade-pill ${gradeClass}">${grade}</div>
            </footer>
        </article>
    `;
}

function escapeHtml(s: string): string {
    return s.replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]!));
}

// ---------- Create Dialog ----------

function openCreateDialog(onDone: () => void): void {
    openModal({
        title: '新建项目',
        body: `
            <div class="form">
                <div class="form-row">
                    <label class="form-label" for="fld-name">项目名称 <span class="required">*</span></label>
                    <input class="input" id="fld-name" type="text" placeholder="例如: 电商后端" required>
                    <div class="form-hint">将作为项目唯一标识</div>
                </div>
                <div class="form-row">
                    <label class="form-label" for="fld-desc">描述</label>
                    <textarea class="textarea" id="fld-desc" rows="3" placeholder="项目用途、技术栈（可选）"></textarea>
                </div>
                <div class="form-row">
                    <label class="form-label" for="fld-lang">主要语言 <span class="required">*</span></label>
                    <select class="select" id="fld-lang" required>
                        <option value="python">Python</option>
                        <option value="java">Java</option>
                        <option value="multi">多语言</option>
                    </select>
                </div>
            </div>
        `,
        footer: `
            <button class="btn btn-secondary btn-sm" data-action="cancel">取消</button>
            <button class="btn btn-primary btn-sm" data-action="submit">创建项目</button>
        `,
        onMount: (modal) => {
            (modal.querySelector('#fld-name') as HTMLInputElement)?.focus();
            modal.querySelector('[data-action=cancel]')?.addEventListener('click', () => closeModal());
            modal.querySelector('[data-action=submit]')?.addEventListener('click', async () => {
                const name = (modal.querySelector('#fld-name') as HTMLInputElement).value.trim();
                const desc = (modal.querySelector('#fld-desc') as HTMLTextAreaElement).value.trim();
                const lang = (modal.querySelector('#fld-lang') as HTMLSelectElement).value;
                if (!name) { toast.warning('项目名称不能为空'); return; }

                const btn = modal.querySelector('[data-action=submit]') as HTMLButtonElement;
                btn.disabled = true;
                btn.textContent = '创建中...';
                const res = await projectApi.create({ name, description: desc || undefined, language: lang });
                btn.disabled = false;
                btn.textContent = '创建项目';

                if (res.error) {
                    toast.error({ title: '创建失败', message: res.error });
                    return;
                }
                toast.success({ title: '创建成功', message: `项目「${name}」已创建` });
                closeModal();
                onDone();
            });
        },
    });
}

// ---------- Upload Dialog ----------

function openUploadDialog(projectId: number, onDone: () => void): void {
    openModal({
        title: '上传代码',
        body: `
            <div class="form">
                <div class="form-row">
                    <label class="form-label" for="fld-version">版本标签</label>
                    <input class="input" id="fld-version" type="text" value="v1.0" placeholder="例如: v1.0 / main / 2025-03">
                </div>
                <div class="form-row">
                    <label class="form-label">代码包 <span class="required">*</span></label>
                    <div class="file-drop" id="file-drop">
                        <input type="file" id="fld-file" accept=".zip" hidden>
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                        <div class="file-drop-title">点击选择或拖拽 ZIP 到此处</div>
                        <div class="file-drop-hint">仅支持 .zip 格式，最大 100MB</div>
                        <div class="file-drop-selected" id="file-selected" hidden></div>
                    </div>
                </div>
                <label class="checkbox">
                    <input type="checkbox" id="fld-autoscan" checked>
                    <span>上传完成后立即触发扫描</span>
                </label>
            </div>
        `,
        footer: `
            <button class="btn btn-secondary btn-sm" data-action="cancel">取消</button>
            <button class="btn btn-primary btn-sm" data-action="submit" disabled>上传</button>
        `,
        onMount: (modal) => {
            const drop = modal.querySelector('#file-drop') as HTMLElement;
            const input = modal.querySelector('#fld-file') as HTMLInputElement;
            const submitBtn = modal.querySelector('[data-action=submit]') as HTMLButtonElement;
            const selEl = modal.querySelector('#file-selected') as HTMLElement;

            const handleFile = (f: File | null) => {
                if (!f) return;
                if (!f.name.toLowerCase().endsWith('.zip')) {
                    toast.error('仅支持 .zip 文件');
                    return;
                }
                selEl.hidden = false;
                selEl.textContent = `${f.name} · ${(f.size / 1024 / 1024).toFixed(2)} MB`;
                submitBtn.disabled = false;
            };

            drop.addEventListener('click', () => input.click());
            input.addEventListener('change', () => handleFile(input.files?.[0] || null));

            drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('drag'); });
            drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
            drop.addEventListener('drop', (e) => {
                e.preventDefault();
                drop.classList.remove('drag');
                const f = e.dataTransfer?.files[0] || null;
                if (f) {
                    const dt = new DataTransfer();
                    dt.items.add(f);
                    input.files = dt.files;
                    handleFile(f);
                }
            });

            modal.querySelector('[data-action=cancel]')?.addEventListener('click', () => closeModal());
            submitBtn.addEventListener('click', async () => {
                const f = input.files?.[0];
                if (!f) return;
                const tag = (modal.querySelector('#fld-version') as HTMLInputElement).value.trim() || 'v1.0';
                const autoscan = (modal.querySelector('#fld-autoscan') as HTMLInputElement).checked;

                submitBtn.disabled = true;
                submitBtn.textContent = '上传中...';

                const up = await scanApi.upload(projectId, tag, f);
                if (up.error || !up.data) {
                    toast.error({ title: '上传失败', message: up.error || '未知错误' });
                    submitBtn.disabled = false;
                    submitBtn.textContent = '上传';
                    return;
                }
                toast.success({ title: '上传成功', message: `版本 ${tag} 已创建` });

                if (autoscan && up.data.id) {
                    const s = await scanApi.start(up.data.id);
                    if (s.error) toast.warning({ title: '扫描未启动', message: s.error });
                    else toast.info({ title: '扫描已启动', message: `任务 #${s.data?.id} 正在后台运行` });
                }

                closeModal();
                onDone();
            });
        },
    });
}
