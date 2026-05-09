export class Router {
    private containerId: string;

    constructor(containerId: string) {
        this.containerId = containerId;
    }

    public navigate(viewRenderFn: (container: HTMLElement) => void) {
        const container = document.getElementById(this.containerId);
        if (!container) {
            throw new Error(`Container ${this.containerId} not found`);
        }

        container.innerHTML = '';

        const viewWrapper = document.createElement('div');
        viewWrapper.className = 'view-container';

        viewRenderFn(viewWrapper);
        container.appendChild(viewWrapper);
    }
}

export const router = new Router('main-content');
