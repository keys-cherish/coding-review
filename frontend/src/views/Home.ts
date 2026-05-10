import { systemApi, projectApi, ruleApi } from '../api';
import { router } from '../router';

interface Feature {
    kicker: string;
    title: string;
    desc: string;
    tags: string[];
    color: string;
}

const features: Feature[] = [
    {
        kicker: 'ARCH',
        title: '把依赖关系变成架构地图',
        desc: '跨文件依赖、调用链、继承关系和循环依赖一次生成，复杂项目也能快速看清边界。',
        tags: ['依赖图', '调用图', 'Tarjan SCC'],
        color: '#c96f4d',
    },
    {
        kicker: 'RADAR',
        title: '六维雷达量化架构健康度',
        desc: '架构清晰度、分层隔离度、模块解耦度、组件内聚度、规范执行力、重复冗余度集中呈现。',
        tags: ['6D 评分', '趋势对比', '风险定位'],
        color: '#9f5f3e',
    },
    {
        kicker: 'RULES',
        title: '规则、配置与安全问题同屏扫描',
        desc: '同时覆盖 Python、Java 与配置文件，识别坏味道、复杂度、硬编码密钥和调试开关。',
        tags: ['代码规范', '配置扫描', '安全检查'],
        color: '#2f6f5e',
    },
    {
        kicker: 'REPORT',
        title: '面向汇报的图形化产物',
        desc: 'UML、ER、火焰图、Treemap 和报告中心，让课程展示与团队评审都有抓手。',
        tags: ['UML', 'ER 图', '报告导出'],
        color: '#3d5a80',
    },
];

const workflows = [
    { step: '01', title: '创建项目', desc: '录入项目与语言栈，建立扫描档案。' },
    { step: '02', title: '上传源码', desc: '上传 ZIP 包，本地解析源码与配置。' },
    { step: '03', title: '执行扫描', desc: '生成问题、图谱、雷达与重构建议。' },
    { step: '04', title: '汇报改进', desc: '导出报告，按优先级推进重构。' },
];

const marqueeItems = [
    'Tree-sitter', 'Python', 'Java', 'Config', 'Dependency Graph', 'Call Graph',
    'UML', 'ER Diagram', 'Radar', 'Treemap', 'Flame Graph', 'Refactor Plan',
    'MVC', 'DDD', 'Clean Architecture', 'Cycle Detection', 'Security Rules',
];

export async function renderHome(container: HTMLElement): Promise<void> {
    container.innerHTML = `
        <div class="home landing-home">
            <section class="home-hero landing-hero">
                <div class="hero-bg">
                    <div class="grid-lines"></div>
                    <div class="landing-outline landing-outline-a"></div>
                    <div class="landing-outline landing-outline-b"></div>
                </div>

                <div class="landing-navline">
                    <span>CodeGuard Pro</span>
                    <nav>
                        <button data-jump="features">Highlights</button>
                        <button data-jump="workflow">Workflow</button>
                        <button data-jump="reports">Reports</button>
                    </nav>
                </div>

                <div class="landing-hero-grid">
                    <div class="hero-wrap landing-copy">
                        <div class="hero-badge">
                            <span class="hero-badge-dot"></span>
                            Local-first architecture intelligence
                        </div>

                        <p class="landing-overline">静态分析 · 架构可视化 · 重构建议</p>
                        <h1 class="home-title landing-title">
                            Make code architecture visible.
                            <span>让软件结构一眼被看懂。</span>
                        </h1>

                        <p class="home-subtitle landing-subtitle">
                            CodeGuard Pro 把源码扫描、架构图谱、六维雷达和重构建议整合成一个本地工作台，
                            让课程项目不只是“能运行”，而是有清晰的工程亮点。
                        </p>

                        <div class="home-cta landing-actions">
                            <button class="btn btn-primary btn-lg" id="cta-start">开始扫描项目</button>
                            <button class="btn btn-secondary btn-lg" id="cta-rules">查看规则库</button>
                        </div>

                        <div class="hero-stats landing-stats" id="hero-stats">
                            <div class="hero-stat">
                                <div class="hero-stat-v" id="hs-projects">—</div>
                                <div class="hero-stat-k">Projects</div>
                            </div>
                            <div class="hero-stat-sep"></div>
                            <div class="hero-stat">
                                <div class="hero-stat-v" id="hs-rules">—</div>
                                <div class="hero-stat-k">Rules</div>
                            </div>
                            <div class="hero-stat-sep"></div>
                            <div class="hero-stat">
                                <div class="hero-stat-v" id="hs-langs">—</div>
                                <div class="hero-stat-k">Languages</div>
                            </div>
                            <div class="hero-stat-sep"></div>
                            <div class="hero-stat">
                                <div class="hero-stat-v"><span class="dot dot-success"></span>Online</div>
                                <div class="hero-stat-k" id="hs-version">—</div>
                            </div>
                        </div>
                    </div>

                    <div class="landing-product-card" aria-hidden="true">
                        <div class="product-window">
                            <div class="product-window-head">
                                <span></span><span></span><span></span>
                                <b>architecture.scan</b>
                            </div>
                            <div class="product-score-row">
                                <div>
                                    <p>Architecture score</p>
                                    <strong>87.5</strong>
                                </div>
                                <span>A</span>
                            </div>
                            <div class="product-radar">
                                <svg viewBox="0 0 220 170">
                                    <polygon points="110,10 190,48 172,134 48,134 30,48" />
                                    <polygon points="110,36 163,62 150,116 68,116 56,62" />
                                    <polygon class="radar-fill" points="110,18 176,56 160,124 58,128 42,56" />
                                    <circle cx="110" cy="18" r="4" />
                                    <circle cx="176" cy="56" r="4" />
                                    <circle cx="160" cy="124" r="4" />
                                    <circle cx="58" cy="128" r="4" />
                                    <circle cx="42" cy="56" r="4" />
                                </svg>
                            </div>
                            <div class="product-bars">
                                <div><span>Layer isolation</span><b style="width:86%"></b></div>
                                <div><span>Module cohesion</span><b style="width:78%"></b></div>
                                <div><span>Duplication risk</span><b style="width:24%"></b></div>
                            </div>
                        </div>

                        <div class="install-card">
                            <div class="install-card-label">Run locally</div>
                            <code>pnpm dev</code>
                            <code>python -m backend.main</code>
                        </div>
                    </div>
                </div>
            </section>

            <section class="marquee-section landing-marquee">
                <div class="marquee-label">分析能力矩阵</div>
                <div class="marquee">
                    <div class="marquee-track">
                        ${[...marqueeItems, ...marqueeItems].map(t => `<span class="marquee-item">${t}</span>`).join('')}
                    </div>
                </div>
            </section>

            <section class="home-section landing-section" id="features">
                <div class="section-index">01</div>
                <header class="home-section-head landing-section-head">
                    <div class="eyebrow">Highlights</div>
                    <h2 class="home-section-title">首页应该先展示“为什么值得看”</h2>
                    <p class="home-section-sub">把最能体现工程亮点的图谱、雷达、规则和报告能力前置。</p>
                </header>

                <div class="feature-grid landing-feature-grid">
                    ${features.map((f, i) => `
                        <article class="feature-card landing-feature-card" style="--accent:${f.color}" data-idx="${i}">
                            <div class="feature-card-accent"></div>
                            <div class="feature-kicker">${f.kicker}</div>
                            <h3 class="feature-title">${f.title}</h3>
                            <p class="feature-desc">${f.desc}</p>
                            <div class="feature-tags">
                                ${f.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                            </div>
                        </article>
                    `).join('')}
                </div>
            </section>

            <section class="home-section product-section" id="reports">
                <div class="section-index">02</div>
                <div class="product-copy">
                    <div class="eyebrow">Product story</div>
                    <h2 class="home-section-title">从扫描结果到重构任务，不再只是一张问题表。</h2>
                    <p class="home-section-sub">架构雷达负责判断整体健康度，依赖图负责定位结构风险，重构建议负责把问题转成可执行清单。</p>
                    <button class="btn btn-secondary" id="cta-refactor">查看重构建议</button>
                </div>
                <div class="report-stack">
                    <div class="report-card report-card-main">
                        <span>Priority #1</span>
                        <strong>拆分高复杂度核心方法</strong>
                        <p>收益 high · 成本 medium · 影响 4 个文件</p>
                    </div>
                    <div class="report-card">
                        <span>Dependency cycle</span>
                        <strong>service → repository → service</strong>
                    </div>
                    <div class="report-card">
                        <span>Config security</span>
                        <strong>发现硬编码密钥与调试开关</strong>
                    </div>
                </div>
            </section>

            <section class="home-section workflow-section" id="workflow">
                <div class="section-index">03</div>
                <header class="home-section-head landing-section-head">
                    <div class="eyebrow">Workflow</div>
                    <h2 class="home-section-title">四步把项目讲清楚</h2>
                    <p class="home-section-sub">更适合答辩展示、团队评审和后续迭代。</p>
                </header>

                <div class="workflow-row landing-workflow-row">
                    ${workflows.map(w => `
                        <div class="workflow-item">
                            <div class="workflow-step">${w.step}</div>
                            <div class="workflow-title">${w.title}</div>
                            <div class="workflow-desc">${w.desc}</div>
                        </div>
                    `).join('')}
                </div>
            </section>

            <section class="home-cta-banner landing-cta-banner">
                <div class="cta-bg"></div>
                <div class="cta-content">
                    <p class="landing-overline">Start from your first scan</p>
                    <h2 class="cta-title">让首页先抓住人，再把用户带进扫描流程。</h2>
                    <p class="cta-desc">创建第一个项目，生成架构雷达、依赖图和重构建议。</p>
                    <button class="btn btn-primary btn-lg" id="cta-final">立即开始</button>
                </div>
            </section>
        </div>
    `;

    const goProjects = () => router.navigate('projects');
    const goRules = () => router.navigate('rules');
    container.querySelector('#cta-start')?.addEventListener('click', goProjects);
    container.querySelector('#cta-final')?.addEventListener('click', goProjects);
    container.querySelector('#cta-rules')?.addEventListener('click', goRules);
    container.querySelector('#cta-refactor')?.addEventListener('click', () => router.navigate('refactor'));
    container.querySelectorAll<HTMLElement>('[data-jump]').forEach(button => {
        button.addEventListener('click', () => {
            const target = container.querySelector(`#${button.dataset.jump}`);
            target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    container.querySelectorAll<HTMLElement>('.feature-card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            card.style.setProperty('--mx', `${e.clientX - rect.left}px`);
            card.style.setProperty('--my', `${e.clientY - rect.top}px`);
        });
    });

    const [projectsResp, rulesResp, infoResp] = await Promise.all([
        projectApi.list(),
        ruleApi.stats(),
        systemApi.info(),
    ]);

    const $ = (sel: string) => container.querySelector(sel) as HTMLElement | null;

    if (projectsResp.data) {
        animateNumber($('#hs-projects'), projectsResp.data.length);
    }
    if (rulesResp.data) {
        animateNumber($('#hs-rules'), rulesResp.data.total);
    }
    if (infoResp.data) {
        animateNumber($('#hs-langs'), infoResp.data.supported_languages.length);
        const v = $('#hs-version');
        if (v) v.textContent = `v${infoResp.data.version}`;
    }
}

function animateNumber(el: HTMLElement | null, target: number): void {
    if (!el) return;
    const duration = 800;
    const start = performance.now();
    const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
    const tick = (now: number) => {
        const t = Math.min((now - start) / duration, 1);
        el.textContent = String(Math.round(target * easeOut(t)));
        if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
}
