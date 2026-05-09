import { initCharts } from '../utils/charts';

export function renderDashboard(container: HTMLElement) {
    container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 32px;">
        <h2 style="font-family: Georgia, serif; font-size: 32px;">监控大盘</h2>
        <div style="color: var(--text-light); font-size: 14px;">上次扫描: 刚刚更新</div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 32px;">
        <!-- 统计卡片 1 -->
        <div style="background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="font-size: 14px; color: var(--text-light); font-weight: 500;">综合代码健康度</div>
            <div style="font-size: 36px; font-weight: bold; color: var(--primary); margin: 8px 0; font-family: Georgia, serif;">A+</div>
            <div style="color: var(--success); font-size: 13px;">↑ 较上版本提升 12%</div>
        </div>
        <!-- 统计卡片 2 -->
        <div style="background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="font-size: 14px; color: var(--text-light); font-weight: 500;">技术债预估 (时)</div>
            <div style="font-size: 36px; font-weight: bold; color: var(--text-dark); margin: 8px 0; font-family: Georgia, serif;">24.5</div>
            <div style="color: var(--warning); font-size: 13px;">需关注核心模块</div>
        </div>
        <!-- 统计卡片 3 -->
        <div style="background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="font-size: 14px; color: var(--text-light); font-weight: 500;">千行代码缺陷率</div>
            <div style="font-size: 36px; font-weight: bold; color: var(--text-dark); margin: 8px 0; font-family: Georgia, serif;">1.2</div>
            <div style="color: var(--success); font-size: 13px;">优于团队平均线</div>
        </div>
        <!-- 统计卡片 4 -->
        <div style="background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
            <div style="font-size: 14px; color: var(--text-light); font-weight: 500;">重复代码占比</div>
            <div style="font-size: 36px; font-weight: bold; color: var(--text-dark); margin: 8px 0; font-family: Georgia, serif;">4.8%</div>
            <div style="color: var(--text-light); font-size: 13px;">持平</div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px; margin-bottom: 24px;">
        <div style="background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid var(--border-color); height: 400px; display: flex; flex-direction: column;">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">📈 质量得分动态演进 (实时流式推送模拟)</div>
            <div id="trendChart" style="flex: 1; width: 100%;"></div>
        </div>
        <div style="background: var(--card-bg); padding: 24px; border-radius: 16px; border: 1px solid var(--border-color); height: 400px; display: flex; flex-direction: column;">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">⭐ 五维评估雷达图</div>
            <div id="radarChart" style="flex: 1; width: 100%;"></div>
        </div>
    </div>
  `;

    // 确保 DOM 挂载完成后再初始化 ECharts
    setTimeout(() => {
        initCharts();
    }, 0);
}
