type ToastKind = 'info' | 'success' | 'warning' | 'danger';

interface ToastOpt {
    title?: string;
    message: string;
    duration?: number;
}

function ensureContainer(): HTMLElement {
    let c = document.getElementById('toast-container');
    if (!c) {
        c = document.createElement('div');
        c.id = 'toast-container';
        c.className = 'toast-container';
        document.body.appendChild(c);
    }
    return c;
}

function show(kind: ToastKind, opt: ToastOpt | string): void {
    const o: ToastOpt = typeof opt === 'string' ? { message: opt } : opt;
    const el = document.createElement('div');
    el.className = `toast toast-${kind}`;
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');

    const icons: Record<ToastKind, string> = {
        info:    '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
        success: '<circle cx="12" cy="12" r="10"/><path d="M8 12l2.5 2.5L16 9"/>',
        warning: '<path d="M12 3l10 18H2L12 3Z"/><path d="M12 10v5M12 18h.01"/>',
        danger:  '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/>',
    };

    el.innerHTML = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${icons[kind]}</svg>
        <div class="toast-body">
            ${o.title ? `<div class="toast-title">${o.title}</div>` : ''}
            <div class="toast-message">${o.message}</div>
        </div>
        <button class="toast-close" aria-label="关闭">×</button>
    `;

    const container = ensureContainer();
    container.appendChild(el);
    // 触发入场动画
    requestAnimationFrame(() => el.classList.add('show'));

    const close = () => {
        el.classList.remove('show');
        el.addEventListener('transitionend', () => el.remove(), { once: true });
        setTimeout(() => el.remove(), 400);
    };
    el.querySelector('.toast-close')?.addEventListener('click', close);

    const duration = o.duration ?? (kind === 'danger' ? 6000 : 3500);
    if (duration > 0) setTimeout(close, duration);
}

export const toast = {
    info:    (opt: ToastOpt | string) => show('info', opt),
    success: (opt: ToastOpt | string) => show('success', opt),
    warning: (opt: ToastOpt | string) => show('warning', opt),
    error:   (opt: ToastOpt | string) => show('danger', opt),
};
