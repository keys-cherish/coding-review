/**
 * 通用 Modal 组件。
 * - Escape 关闭
 * - 点击遮罩关闭
 * - 焦点陷阱（简化版：只记忆返回焦点）
 */

export interface ModalOpt {
    title: string;
    body: string;
    footer?: string;
    width?: string;
    onMount?: (modal: HTMLElement) => void;
    onClose?: () => void;
}

let currentModal: HTMLElement | null = null;
let onCloseCurrent: (() => void) | null = null;
let lastFocused: HTMLElement | null = null;

export function openModal(opt: ModalOpt): void {
    closeModal();

    lastFocused = document.activeElement as HTMLElement;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.innerHTML = `
        <div class="modal" style="${opt.width ? `width:${opt.width}` : ''}">
            <header class="modal-header">
                <h3 class="modal-title">${opt.title}</h3>
                <button class="modal-close" aria-label="关闭">×</button>
            </header>
            <div class="modal-body">${opt.body}</div>
            ${opt.footer ? `<footer class="modal-footer">${opt.footer}</footer>` : ''}
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
    currentModal = overlay;
    onCloseCurrent = opt.onClose || null;

    // 入场动画
    requestAnimationFrame(() => overlay.classList.add('show'));

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeModal();
    });
    overlay.querySelector('.modal-close')?.addEventListener('click', () => closeModal());

    const escHandler = (e: KeyboardEvent) => {
        if (e.key === 'Escape') closeModal();
    };
    document.addEventListener('keydown', escHandler);
    (overlay as any)._escHandler = escHandler;

    if (opt.onMount) {
        opt.onMount(overlay.querySelector('.modal') as HTMLElement);
    }
}

export function closeModal(): void {
    if (!currentModal) return;
    const el = currentModal;
    const handler = (el as any)._escHandler;
    if (handler) document.removeEventListener('keydown', handler);

    el.classList.remove('show');
    document.body.style.overflow = '';

    setTimeout(() => {
        el.remove();
    }, 200);

    if (onCloseCurrent) {
        try { onCloseCurrent(); } catch {}
    }
    currentModal = null;
    onCloseCurrent = null;

    if (lastFocused) {
        try { lastFocused.focus(); } catch {}
    }
}
