"""端到端扫描流程集成测试。

跑完整 ScanOrchestrator：示例项目 → 解析 → 规则 → 复杂度 → 重复 → 评分 → 落库。
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.engines.rules.registry import discover_rules
from backend.models import (
    ComplexityMetric,
    Issue,
    Project,
    ScanTask,
    SourceFile,
    Version,
)
from backend.services.scan_orchestrator import ScanOrchestrator


@pytest.fixture(scope="session", autouse=True)
def _load_rules() -> None:
    """确保规则注册表填充。"""
    discover_rules()


@pytest_asyncio.fixture
async def db_session(tmp_path):
    """临时 SQLite 数据库。"""
    db_file = tmp_path / "test.db"

    sync_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", future=True)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def scan_target(tmp_path: Path, db_session) -> tuple[int, Path]:
    """搭建一个版本：用 fixtures 构造一份模拟项目目录。"""
    upload = tmp_path / "upload"
    upload.mkdir()

    fixtures = Path(__file__).parent.parent / "fixtures" / "python"
    for f in fixtures.glob("*.py"):
        shutil.copy2(f, upload / f.name)

    project = Project(name="测试项目", description="集成测试", language="python")
    db_session.add(project)
    await db_session.flush()

    version = Version(
        project_id=project.id,
        version_tag="v1.0",
        upload_path=str(upload),
        total_files=0,
        total_lines=0,
    )
    db_session.add(version)
    await db_session.flush()

    task = ScanTask(version_id=version.id)
    db_session.add(task)
    await db_session.flush()
    await db_session.commit()
    return task.id, upload


class TestScanOrchestratorE2E:

    @pytest.mark.asyncio
    async def test_full_scan_pipeline(self, db_session, scan_target) -> None:
        scan_id, _ = scan_target
        orch = ScanOrchestrator()

        await orch.run_scan(scan_id, db_session)
        await db_session.commit()

        task = await db_session.get(ScanTask, scan_id)
        assert task.status == "done", f"扫描未成功完成: status={task.status}, err={task.error_msg}"
        assert task.progress >= 0.99
        assert 0 <= task.overall_score <= 100
        assert task.grade in {"A", "B", "C", "D"}

    @pytest.mark.asyncio
    async def test_scan_produces_issues(self, db_session, scan_target) -> None:
        scan_id, _ = scan_target
        await ScanOrchestrator().run_scan(scan_id, db_session)
        await db_session.commit()

        rs = await db_session.execute(
            select(Issue).where(Issue.scan_task_id == scan_id)
        )
        issues = rs.scalars().all()
        # messy.py 应触发若干问题
        assert len(issues) >= 3
        # 每条都应有规则码与严重度
        for it in issues:
            assert it.rule_code
            assert it.severity in {"error", "warning", "info"}

    @pytest.mark.asyncio
    async def test_scan_produces_complexity_metrics(self, db_session, scan_target) -> None:
        scan_id, _ = scan_target
        await ScanOrchestrator().run_scan(scan_id, db_session)
        await db_session.commit()

        rs = await db_session.execute(select(ComplexityMetric))
        metrics = rs.scalars().all()
        assert len(metrics) >= 1
        names = {m.function_name for m in metrics}
        assert any("super_complex" in n or "BadFunctionName" in n for n in names)

    @pytest.mark.asyncio
    async def test_scan_creates_source_files(self, db_session, scan_target) -> None:
        scan_id, _ = scan_target
        await ScanOrchestrator().run_scan(scan_id, db_session)
        await db_session.commit()

        rs = await db_session.execute(select(SourceFile))
        files = rs.scalars().all()
        assert len(files) >= 2  # 至少 clean.py + messy.py
        for f in files:
            assert 0 <= f.health_score <= 100
            assert f.lines_of_code > 0

    @pytest.mark.asyncio
    async def test_scoring_breakdown_consistency(self, db_session, scan_target) -> None:
        scan_id, _ = scan_target
        await ScanOrchestrator().run_scan(scan_id, db_session)
        await db_session.commit()

        task = await db_session.get(ScanTask, scan_id)
        # 子分数都应在合理范围
        for s in (task.spec_score, task.dup_score, task.complexity_score):
            assert 0 <= s <= 100
        # 综合分应接近三维加权
        weighted = (
            task.spec_score * 0.45
            + task.dup_score * 0.30
            + task.complexity_score * 0.25
        )
        assert abs(task.overall_score - weighted) < 1.0
