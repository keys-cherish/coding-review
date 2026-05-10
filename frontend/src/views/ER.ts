import { comingSoon } from '../components/PageShell';
export function renderER(container: HTMLElement): void {
    container.innerHTML = comingSoon('数据库 ER 图', '扫描 SQL / ORM 模型，自动生成实体关系图。');
}
