/**
 * UML 类图。
 * 左：mermaid 渲染后的 SVG 类图
 * 右：结构化类列表 + Mermaid / PlantUML 源码切换 + 复制
 */
import mermaid from 'mermaid';

import { visApi, type UMLPayload } from '../api';
import { pageShell, emptyState } from '../components/PageShell';
import { mountScanPicker } from '../components/ScanPicker';
import { toast } from '../components/Toast';

let mermaidReady = false;

function initMermaidOnce(): void {
    if (mermaidReady) return;
    mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        themeVariables: {
            primaryColor: '#fdf4f0',
            primaryTextColor: '#3f3f46',
            primaryBorderColor: '#cf7c65',
            lineColor: '#94a3b8',
            fontFamily: 'ui-sans-serif, system-ui, "Segoe UI", sans-serif',
            fontSize: '13px',
        },
    });
    mermaidReady = true;
}

export async function renderUML(container: HTMLElement): Promise<void> {
    initMermaidOnce();

    container.innerHTML = pageShell({
        title: 'UML 类图',
        subtitle: '自动从源码抽取类、字段、方法与继承关系',
        body: `
            <div class="viz-toolbar" id="uml-toolbar"></div>

            <div class="uml-layout" style="margin-top:16px">
                <div class="card uml-main">
                    <div class="card-header">
                        <div class="card-title">类图</div>
                        <div class="uml-switch">
                            <button class="btn btn-sm btn-ghost active" data-src="mermaid">Mermaid</button>
                            <button class="btn btn-sm btn-ghost" data-src="plantuml">PlantUML</button>
                            <button class="btn btn-sm btn-primary" id="uml-copy">复制源码</button>
                        </div>
                    </div>
                    <div class="card-body" id="uml-stage" style="overflow:auto;min-height:520px">
                        <div class="empty-sm">选择扫描以生成类图</div>
                    </div>
                </div>

                <div class="card uml-aside">
                    <div class="card-header">
                        <div class="card-title">类列表</div>
                        <div class="card-subtitle" id="uml-count">—</div>
                    </div>
                    <div class="card-body" id="uml-class-list" style="max-height:680px;overflow:auto"></div>
                </div>
            </div>
        `,
    });

    const toolbar = container.querySelector('#uml-toolbar') as HTMLElement;
    const stage = container.querySelector('#uml-stage') as HTMLElement;

    let lastPayload: UMLPayload | null = null;
    let mode: 'mermaid' | 'plantuml' = 'mermaid';

    const switches = container.querySelectorAll('.uml-switch button[data-src]');
    switches.forEach(btn => {
        btn.addEventListener('click', () => {
            mode = (btn as HTMLElement).dataset.src as 'mermaid' | 'plantuml';
            switches.forEach(b => b.classList.toggle('active', b === btn));
            if (lastPayload) renderStage(stage, lastPayload, mode);
        });
    });
    (container.querySelector('#uml-copy') as HTMLButtonElement).addEventListener('click', () => {
        if (!lastPayload) return;
        const src = mode === 'mermaid' ? lastPayload.mermaid : lastPayload.plantuml;
        navigator.clipboard.writeText(src).then(
            () => toast.success('已复制到剪贴板'),
            () => toast.error('复制失败'),
        );
    });

    await mountScanPicker(toolbar, async (scanId) => {
        stage.innerHTML = `<div class="empty-sm">加载中...</div>`;
        const { data, error } = await visApi.uml(scanId);
        if (error || !data) {
            toast.error(error || 'UML 加载失败');
            return;
        }
        lastPayload = data;
        renderStage(stage, data, mode);
        renderClassList(container, data);
    });
}

async function renderStage(stage: HTMLElement, data: UMLPayload, mode: 'mermaid' | 'plantuml'): Promise<void> {
    if (!data.classes.length) {
        stage.innerHTML = emptyState({ title: '未抽取到类', desc: '项目可能只包含函数或未识别的语言' });
        return;
    }

    if (mode === 'plantuml') {
        stage.innerHTML = `<pre class="uml-src"><code>${escapeHtml(data.plantuml)}</code></pre>`;
        return;
    }

    try {
        const id = `uml-${Date.now()}`;
        const { svg } = await mermaid.render(id, data.mermaid);
        stage.innerHTML = `<div class="uml-svg-wrap">${svg}</div>`;
    } catch (e: any) {
        stage.innerHTML = `
            <div class="uml-error">
                <div class="uml-error-title">Mermaid 渲染失败</div>
                <div class="uml-error-msg">${escapeHtml(e?.message || String(e))}</div>
                <pre class="uml-src"><code>${escapeHtml(data.mermaid)}</code></pre>
            </div>
        `;
    }
}

function renderClassList(container: HTMLElement, data: UMLPayload): void {
    const count = container.querySelector('#uml-count')!;
    const list = container.querySelector('#uml-class-list') as HTMLElement;
    count.textContent = `共 ${data.classes.length} 个类`;

    if (!data.classes.length) {
        list.innerHTML = emptyState({ title: '无类可展示' });
        return;
    }

    list.innerHTML = data.classes.slice(0, 60).map(c => `
        <div class="uml-class">
            <div class="uml-class-head">
                <span class="uml-class-name">${escapeHtml(c.name)}</span>
                ${c.parents.length ? `<span class="uml-class-extends">extends ${c.parents.map(escapeHtml).join(', ')}</span>` : ''}
            </div>
            <div class="uml-class-file">${escapeHtml(c.file)}</div>
            ${c.fields.length ? `
                <div class="uml-section">字段 · ${c.fields.length}</div>
                <ul class="uml-member-list">
                    ${c.fields.slice(0, 8).map(f => `
                        <li><span class="v-${f.visibility}">${f.visibility}</span> ${escapeHtml(f.name)}${f.type ? `: <em>${escapeHtml(f.type)}</em>` : ''}</li>
                    `).join('')}
                    ${c.fields.length > 8 ? `<li class="more">+${c.fields.length - 8} more</li>` : ''}
                </ul>
            ` : ''}
            ${c.methods.length ? `
                <div class="uml-section">方法 · ${c.methods.length}</div>
                <ul class="uml-member-list">
                    ${c.methods.slice(0, 10).map(m => `
                        <li><span class="v-${m.visibility}">${m.visibility}</span> ${escapeHtml(m.name)}(${m.params.map(escapeHtml).join(', ')})${m.returns ? ` → <em>${escapeHtml(m.returns)}</em>` : ''}</li>
                    `).join('')}
                    ${c.methods.length > 10 ? `<li class="more">+${c.methods.length - 10} more</li>` : ''}
                </ul>
            ` : ''}
        </div>
    `).join('');
}

function escapeHtml(s: string): string {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
}
