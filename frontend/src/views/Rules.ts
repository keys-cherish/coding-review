export function renderRules(container: HTMLElement) {
    container.innerHTML = `
    <div style="margin-bottom: 32px;">
        <h2 style="font-family: Georgia, serif; font-size: 32px;">规则引擎配置</h2>
    </div>

    <div style="background: var(--card-bg); border-radius: 16px; border: 1px solid var(--border-color); box-shadow: 0 4px 20px rgba(0,0,0,0.02); overflow: hidden;">
        <div style="padding: 20px 24px; border-bottom: 1px solid var(--border-color); display: flex; gap: 16px; background: #fafafa;">
            <select style="padding: 8px 16px; border-radius: 8px; border: 1px solid #ddd; outline: none;"><option>所有语言</option><option>Java</option><option>TypeScript</option></select>
            <select style="padding: 8px 16px; border-radius: 8px; border: 1px solid #ddd; outline: none;"><option>所有类别</option><option>规范</option><option>复杂度</option></select>
        </div>
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
                <tr>
                    <th style="padding: 16px 24px; font-size: 13px; color: var(--text-light); border-bottom: 1px solid var(--border-color);">规则名称</th>
                    <th style="padding: 16px 24px; font-size: 13px; color: var(--text-light); border-bottom: 1px solid var(--border-color);">描述</th>
                    <th style="padding: 16px 24px; font-size: 13px; color: var(--text-light); border-bottom: 1px solid var(--border-color);">严重级别</th>
                    <th style="padding: 16px 24px; font-size: 13px; color: var(--text-light); border-bottom: 1px solid var(--border-color);">状态</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 16px 24px; font-weight: 500; border-bottom: 1px solid var(--border-color);">MethodCyclomaticComplexity</td>
                    <td style="padding: 16px 24px; border-bottom: 1px solid var(--border-color);">方法圈复杂度超标（>15）</td>
                    <td style="padding: 16px 24px; border-bottom: 1px solid var(--border-color);"><span style="background:#fee2e2; color:var(--danger); padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;">High</span></td>
                    <td style="padding: 16px 24px; border-bottom: 1px solid var(--border-color);">
                        <label style="position:relative; display:inline-block; width:44px; height:24px;">
                            <input type="checkbox" checked style="opacity:0; width:0; height:0;">
                            <span style="position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0; background-color:var(--primary); border-radius:24px; transition:.3s;">
                                <span style="position:absolute; content:''; height:18px; width:18px; left:3px; bottom:3px; background-color:white; border-radius:50%; transform:translateX(20px); transition:.3s;"></span>
                            </span>
                        </label>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
  `;
}
