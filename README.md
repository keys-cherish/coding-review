# CodeGuard Pro · 智能代码质量管理与规范检测平台

> 苏州科技大学《软件工程》实践课题 8 — 代码质量管理与规范检测系统

[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4-42b883)](https://vuejs.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()

CodeGuard Pro 是一款**纯本地、零外部依赖**的代码质量平台。  
上传一份 ZIP 代码包，三秒看清规范、重复、复杂度三维评分，附带可执行的修改建议清单。  
后端 FastAPI + 前端 Vue 3 + ECharts，跨平台运行（Windows / Linux / macOS）。

---

## 目录

- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [系统截图](#系统截图)
- [系统架构](#系统架构)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [开发与测试](#开发与测试)
- [常见问题](#常见问题)
- [评分映射](#评分映射)

---

## 核心特性

| 模块 | 能力 |
|------|------|
| 🔍 **多语言扫描** | Python / Java，命名 / 缩进 / 注释 / 魔法值 / 空格 / 死代码等 20+ 规则 |
| 🧬 **重复代码检测** | Token 级 Rabin-Karp 滚动哈希 + AST 节点归一化双引擎，识别"换皮"重复 |
| ⚡ **复杂度分析** | McCabe 圈复杂度 + Cognitive Complexity，函数级风险分级 |
| ⭐ **三维评分** | 规范度 / 重复度 / 复杂度加权综合，A/B/C/D 四级评定 |
| 📊 **可视化报告** | 雷达图 / 饼图 / 热力树状图 + HTML / PDF / Markdown 三种导出 |
| 🚀 **实时进度** | WebSocket 推送扫描进度，大型项目可见即所得 |
| 🧰 **规则管理** | 内置规则可逐条启停，支持按语言、类别筛选 |
| 📦 **版本对比** | 同一项目多版本管理，便于评分演进追踪 |

---

## 快速开始

### 环境要求

- **Python 3.10 / 3.11 / 3.12**（推荐 3.11，启动脚本默认拉取）
- **uv** — 现代 Python 包管理器，比 pip 快 10-100 倍。脚本会**自动安装**，无需手动准备
- 操作系统：Windows 10/11、Ubuntu 20.04+、macOS 12+
- 浏览器：Chrome / Edge / Firefox（最新版）

### 一键启动（推荐）

**Windows：**
```cmd
start.bat
```

**Linux / macOS：**
```bash
chmod +x start.sh
./start.sh
```

启动脚本会自动完成：
1. 检查 / 安装 **uv**（若未安装则用 pip 装一份到 `--user`）
2. 用 `uv venv --python 3.11` 创建 `.venv`（按需自动下载 Python 解释器）
3. 用 `uv pip install -r requirements.txt` 装依赖
4. 初始化 SQLite 数据库
5. 启动 Uvicorn 服务，浏览器自动打开 `http://127.0.0.1:8000`

> Windows 上失败时窗口不会闪退，每个错误都会停在 `pause`，方便阅读。

### 手动启动

```bash
# 安装 uv（一次性）
curl -LsSf https://astral.sh/uv/install.sh | sh        # Linux/Mac
# 或：
pip install uv                                          # 任意平台

# 项目内
uv venv --python 3.11
uv pip install -r requirements.txt
.venv/bin/python -m scripts.init_db                     # Windows: .venv\Scripts\python.exe
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 验证

打开浏览器访问：

- 主界面 — http://127.0.0.1:8000
- API 文档 — http://127.0.0.1:8000/docs
- 健康检查 — http://127.0.0.1:8000/api/health

---

## 系统截图

> 所有截图位于 `docs/images/screenshots/`。

| 视图 | 说明 |
|------|------|
| ![home](docs/images/screenshots/01-home.png) | 首页项目卡片墙 |
| ![upload](docs/images/screenshots/02-upload.png) | 拖拽上传 ZIP |
| ![progress](docs/images/screenshots/03-progress.png) | 实时扫描进度 |
| ![result](docs/images/screenshots/04-result.png) | 三维评分总览 |
| ![issues](docs/images/screenshots/05-issues.png) | 问题清单 + 代码定位 |
| ![rules](docs/images/screenshots/06-rules.png) | 规则启停管理 |
| ![report](docs/images/screenshots/07-report.png) | 报告导出 |

---

## 系统架构

```
┌────────────────────────────────────────────────────────────┐
│                    Vue 3 SPA (前端)                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │  Home    │ Upload   │ Progress │ Result   │ Rules    │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└──────────────┬─────────────────────────┬───────────────────┘
               │ HTTP / WebSocket        │
┌──────────────▼─────────────────────────▼───────────────────┐
│               FastAPI 应用层 (backend/main.py)              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ projects │  scans   │  issues  │ reports  │  rules   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└──────────────┬─────────────────────────────────────────────┘
               │
┌──────────────▼─────────────────────────────────────────────┐
│                   ScanOrchestrator                         │
│  解析 → 规则 → 复杂度 → 重复 → 评分 → 落库 → WS 广播          │
└──────────────┬─────────────────────────────────────────────┘
               │
        ┌──────┴──────┬────────────┬───────────┐
        ▼             ▼            ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  Parser  │ │  Rules   │ │Complexity│ │   Dup    │
   │  Python  │ │ 20+ Rules│ │  McCabe  │ │ RabinKarp│
   │  Java    │ │ Registry │ │ Cognitive│ │   AST    │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘
        │             │            │           │
        └──────┬──────┴────────────┴───────────┘
               ▼
        ┌────────────────┐
        │ SQLAlchemy ORM │
        │ SQLite (默认)   │
        └────────────────┘
```

### 模块化设计

- **解析层** (`backend/engines/parser/`)：抽象基类 `ParserAdapter`，PythonParser 用 `ast`，JavaParser 用 `javalang`，输出统一的 `ParsedFile`，让上层算法不感知语言细节
- **规则引擎** (`backend/engines/rules/`)：基于 `@register` 装饰器自动注册，单条规则只关心"如何检测"，调度由 `RuleEngine` 编排
- **复杂度引擎** (`backend/engines/complexity/`)：圈复杂度按 McCabe 1976 经典公式实现；Cognitive 按 SonarSource 2018 白皮书实现
- **重复检测** (`backend/engines/duplication/`)：双引擎并行 — Token 滚动哈希定位"复制粘贴"，AST 归一化指纹定位"换变量名"
- **评分引擎** (`backend/engines/scoring/`)：三维评分 + 权重综合，规则与映射明文记录，便于课程答辩时讲清楚

详细架构、序列图、数据库 ER 图见 [docs/architecture.md](docs/architecture.md)。

---

## 使用指南

### 1. 创建项目

首页 → "+ 新建项目"，填写名称、描述、主语言（Python / Java / 混合）。

### 2. 上传代码包

进入项目 → "上传新版本"，将 ZIP 拖入上传区，或点击选择文件。

> 支持 `.zip` 格式，建议单个包不超过 100 MB（可在 `backend/config.py` 调整）。

### 3. 启动扫描

上传成功后点击"启动扫描"。扫描页通过 WebSocket 实时显示：当前文件、进度百分比、已发现问题数。

### 4. 查看结果

扫描完成后跳转到"结果总览"：

- **三维评分卡**：规范 / 重复 / 复杂度
- **雷达图**：直观对比三个维度
- **热力树状图**：每个矩形是一个文件，面积=问题数，颜色=健康度
- **Top 规则**：触发最频繁的规则排行

### 5. 问题清单

侧边过滤：严重度（严重 / 警告 / 提示）、规则、关键词。  
点击单条问题展开：相关代码片段（高亮目标行）+ 修改建议。

### 6. 重复 / 复杂度

- **重复代码块**：每块展示出现位置、token 数、行数
- **复杂度排行榜**：函数级气泡图 + 详细表格

### 7. 报告导出

支持三种格式：

| 格式 | 用途 |
|------|------|
| HTML | 交互式网页，独立可分发，便于团队 review |
| PDF | 打印归档（基于 HTML 转换） |
| Markdown | 整合到 Wiki / Issue / 课程报告 |

### 8. 规则管理

`/rules` 页面：按语言 / 类别 / 关键词过滤所有内置规则，点击开关即时启停。  
启停状态同步到内存 `rule_registry`，下一次扫描立即生效。

---

## 项目结构

```
项目/
├── README.md                          ← 本文件
├── LICENSE                            ← MIT
├── requirements.txt                   ← Python 依赖
├── pyproject.toml                     ← 项目元信息
├── start.bat / start.sh               ← 一键启动
│
├── backend/                           ← FastAPI 后端
│   ├── main.py                        ← 应用入口
│   ├── config.py                      ← 配置（pydantic-settings）
│   ├── database.py                    ← SQLAlchemy 引擎
│   ├── engines/                       ← 五大引擎
│   │   ├── parser/                    ← 代码解析（py/java）
│   │   ├── rules/                     ← 规则引擎 + 内置规则
│   │   ├── complexity/                ← 圈/认知复杂度
│   │   ├── duplication/               ← Token + AST 双引擎
│   │   └── scoring/                   ← 三维评分
│   ├── models/                        ← ORM 模型
│   ├── schemas/                       ← Pydantic Schema
│   ├── routers/                       ← REST 路由 + WebSocket
│   ├── services/                      ← 业务编排（scan / report / upload / ws）
│   ├── reports/                       ← HTML/PDF/MD 渲染
│   └── utils/                         ← 工具函数
│
├── frontend/                          ← Vue 3 SPA
│   ├── index.html
│   ├── css/theme.css                  ← 自定义深色主题
│   └── js/
│       ├── api.js                     ← 后端 API 封装
│       ├── store.js                   ← 全局响应式状态
│       ├── router.js                  ← Hash 路由
│       ├── components/                ← 通用组件 + ECharts 图表
│       ├── pages/                     ← 11 个路由页面
│       └── app.js                     ← 主应用装配
│
├── tests/                             ← 测试套件
│   ├── unit/                          ← 5 个单元测试模块（52 用例）
│   ├── integration/                   ← 端到端 + 报告渲染（10 用例）
│   └── fixtures/                      ← 测试输入文件
│
├── examples/                          ← 示例代码包
│   ├── sample_python_project/
│   └── sample_java_project/
│
├── docs/                              ← 详细文档
│   ├── architecture.md                ← 系统架构详解
│   ├── user_guide.md                  ← 使用手册
│   ├── api.md                         ← REST API 列表
│   └── images/                        ← 架构图与截图
│
├── scripts/
│   ├── init_db.py                     ← 数据库初始化
│   └── seed_rules.py                  ← 内置规则入库
│
├── cli/                               ← 命令行工具（占位）
│
└── data/                              ← 运行时数据（自动创建）
    ├── codeguard.db                   ← SQLite 数据库
    ├── uploads/                       ← 上传的代码包
    └── reports/                       ← 生成的报告文件
```

---

## 开发与测试

### 运行测试

```bash
# 全部测试
python -m pytest

# 仅单元测试（快速）
python -m pytest tests/unit -q

# 仅集成测试
python -m pytest tests/integration -q

# 覆盖率报告
python -m pytest --cov=backend --cov-report=term-missing
```

当前测试统计：

| 类型 | 文件 | 用例数 |
|------|------|--------|
| 单元 | parser / complexity / scoring / rules / duplication | 52 |
| 集成 | scan_e2e / reports | 10 |
| **合计** | | **62** |

### 调整配置

通过环境变量或 `.env` 文件覆盖（前缀 `CODEGUARD_`）：

```bash
CODEGUARD_PORT=9000
CODEGUARD_DEBUG=true
CODEGUARD_SCORE_WEIGHT_SPEC=0.5
CODEGUARD_DUP_WINDOW_SIZE=40
```

完整字段见 `backend/config.py` 的 `Settings` 类。

### 添加新规则

```python
# backend/engines/rules/python/my_rule.py
from backend.engines.rules.base import Issue, Rule
from backend.engines.rules.registry import register

@register
class MyCustomRule(Rule):
    code = "PY-X001"
    language = "python"
    category = "naming"
    severity = "warning"
    name = "我的自定义规则"
    description = "..."
    suggestion_template = "..."

    def check(self, parsed):
        issues = []
        # ... 检测逻辑 ...
        return issues
```

重启服务即生效。

---

## 常见问题

**Q：上传 ZIP 后扫描立即"失败"？**  
A：检查 ZIP 内是否有支持语言的源文件（`.py` / `.java`）。如果项目根目录是 `src/`，请确保 ZIP 解压后能直接见到代码文件。

**Q：扫描很慢？**  
A：千行项目通常 1-3 秒。慢的原因常见两类：
1. ZIP 中混入了 `node_modules` / `__pycache__` / `target/`，请清理后重新打包
2. `dup_window_size` 设得太小（默认 50 token），重复检测会变慢

**Q：报告中文乱码？**  
A：报告文件统一 UTF-8 编码，浏览器请确认编码识别。如果是 PDF，确保系统字体支持中文。

**Q：能不能扫描 Git 仓库？**  
A：当前版本只支持 ZIP 上传。可以本地 `git archive --format=zip HEAD -o project.zip` 后上传。

**Q：如何加新语言（如 JavaScript）？**  
A：实现 `ParserAdapter` 子类并注册即可，详见 `docs/architecture.md` 中的"扩展指南"章节。

---

## 评分映射

本项目针对《软件工程实践课题 8 评分标准》的覆盖说明：

| 评分项 | 实现位置 |
|--------|---------|
| 项目管理：创建、上传、设置语言、版本 | `routers/projects.py` + 前端 HomePage / ProjectDetailPage / UploadPage |
| 代码上传与解析 | `services/upload_service.py` + `engines/parser/` |
| 编码规范检测：命名、缩进、注释、空格、魔法值、无效代码 | `engines/rules/{python,java}/` 各 9-10 条规则 |
| 重复率检测：复制粘贴、重复方法、片段 | `engines/duplication/` 双引擎 |
| 复杂度分析：方法行数、圈复杂度 | `engines/complexity/` |
| 问题清单与定位：位置、原因、修改建议 | `routers/issues.py` + 前端 IssuesPage（带代码片段高亮） |
| 质量评分与排名 | `engines/scoring/` 三维加权 |
| 检测报告导出 | `reports/` HTML / PDF / MD |

更详细的评分自评请参考 `docs/scoring_self_eval.md`。

---

## License

MIT © 2026 苏州科技大学软件工程实践课团队
