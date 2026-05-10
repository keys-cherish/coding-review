"""
CodeGuard Pro · FastAPI 应用入口

承载：
- REST API（/api 前缀）
- WebSocket 实时进度推送（/ws）
- 前端静态资源（/）
- 自动 OpenAPI 文档（/docs, /redoc）
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_database
from backend.utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f" {settings.app_name} v{settings.app_version} 启动中")
    logger.info("=" * 60)
    init_database()

    # 注册内置规则到数据库
    from scripts.seed_rules import seed_builtin_rules
    seed_builtin_rules()

    logger.info(f" 服务监听: http://{settings.host}:{settings.port}")
    logger.info(f" API 文档: http://{settings.host}:{settings.port}/docs")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ---------- 路由注册 ----------
from backend.routers import projects, scans, issues, reports, rules, websocket, visualization  # noqa: E402

app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(scans.router, prefix="/api/scans", tags=["扫描任务"])
app.include_router(visualization.router, prefix="/api/scans", tags=["架构可视化"])
app.include_router(issues.router, prefix="/api/issues", tags=["问题清单"])
app.include_router(reports.router, prefix="/api/reports", tags=["检测报告"])
app.include_router(rules.router, prefix="/api/rules", tags=["规则管理"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/api/health", tags=["系统"])
async def health():
    """健康检查端点。"""
    return {
        "status": "ok",
        "name": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/api/info", tags=["系统"])
async def info():
    """系统信息。"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "supported_languages": list(settings.supported_languages),
        "scan_concurrency": settings.scan_concurrency,
        "score_weights": {
            "spec": settings.score_weight_spec,
            "duplication": settings.score_weight_dup,
            "complexity": settings.score_weight_complexity,
        },
    }


# ---------- 前端静态资源 ----------
if settings.frontend_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=settings.frontend_dir),
        name="frontend",
    )

    @app.get("/", include_in_schema=False)
    async def index():
        idx = settings.frontend_dir / "index.html"
        if idx.exists():
            return FileResponse(idx)
        return JSONResponse({"detail": "前端未部署"}, status_code=404)

    @app.get("/{path:path}", include_in_schema=False)
    async def spa_fallback(path: str):
        """SPA 前端回退：未知路径全部返回 index.html，由前端路由处理。"""
        if path.startswith("api") or path.startswith("ws") or path.startswith("docs"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = settings.frontend_dir / path
        if target.is_file():
            return FileResponse(target)
        idx = settings.frontend_dir / "index.html"
        return FileResponse(idx) if idx.exists() else JSONResponse({"detail": "Not Found"}, status_code=404)
