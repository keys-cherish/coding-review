import { router } from '../router';
import { renderDashboard } from './Dashboard';

export function renderHome(container: HTMLElement) {
    container.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 60px; align-items: center; min-height: 70vh;">
      <div>
          <h1 style="font-family: Georgia, serif; font-size: 64px; color: #111; line-height: 1.1; margin-bottom: 24px; letter-spacing: -0.5px;">优雅与力量的<br>代码网关。</h1>
          <p style="font-size: 18px; color: var(--text-light); line-height: 1.7; margin-bottom: 32px; max-width: 500px;">
              不再被繁杂的静态分析工具束缚。CodeGuard 采用双引擎架构，在终端或 CI/CD 中瞬间分析代码复杂度、重复率与规范性。如同艺术品般呈现您的代码质量。
          </p>
          <button id="btn-enter" class="btn-primary">进入控制台 ➔</button>
      </div>
      <div style="text-align: center;">
          <svg viewBox="0 0 240 240" style="width: 100%; max-width: 500px; animation: float 6s ease-in-out infinite;">
              <style>
                @keyframes float { 0% { transform: translateY(0); } 50% { transform: translateY(-15px); } 100% { transform: translateY(0); } }
              </style>
              <circle cx="120" cy="120" r="100" fill="none" stroke="rgba(244, 232, 228, 0.5)" stroke-width="2" />
              <circle cx="120" cy="120" r="80" fill="none" stroke="rgba(244, 232, 228, 0.8)" stroke-width="4" />
              <path d="M120 30 L190 60 L190 120 C190 170 120 210 120 210 C120 210 50 170 50 120 L50 60 Z" fill="#fcfcfb" stroke="#cf7c65" stroke-width="8" stroke-linejoin="round" />
              <path d="M100 90 L80 120 L100 150 M140 90 L160 120 L140 150" fill="none" stroke="#cf7c65" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" />
              <circle cx="120" cy="120" r="8" fill="#cf7c65">
                  <animate attributeName="r" values="6;10;6" dur="2s" repeatCount="indefinite"/>
              </circle>
          </svg>
      </div>
    </div>
  `;

    // 绑定内部跳转
    container.querySelector('#btn-enter')?.addEventListener('click', () => {
        // 同步更新 Header 状态，并跳转
        document.querySelector('.nav-links a[data-target="dashboard"]')?.dispatchEvent(new Event('click'));
    });
}
