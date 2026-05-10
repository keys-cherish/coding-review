import { comingSoon } from '../components/PageShell';

export function renderScans(container: HTMLElement): void {
    container.innerHTML = comingSoon(
        '扫描历史',
        '每次扫描的完整记录、状态、评分与下钻查看。即将在下一迭代上线。'
    );
}
