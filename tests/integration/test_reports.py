"""报告渲染集成测试。"""
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.database import Base
from backend.engines.rules.registry import discover_rules
from backend.models import Project, ScanTask, Version
from backend.services.report_service import collect_report_data, generate_report
from backend.reports.markdown_renderer import render_markdown
from backend.reports.html_renderer import render_html
from backend.services.scan_orchestrator import ScanOrchestrator


@pytest.fixture(scope="session", autouse=True)
def _load_rules() -> None:
    discover_rules()


@pytest_asyncio.fixture
async def session_with_scan(tmp_path):
    import shutil
    db_file = tmp_path / "rep.db"
    sync_engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", future=True)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    upload = tmp_path / "code"
    upload.mkdir()
    fixtures = Path(__file__).parent.parent / "fixtures" / "python"
    for f in fixtures.glob("*.py"):
        shutil.copy2(f, upload / f.name)

    async with SessionLocal() as session:
        project = Project(name="报告测试", language="python")
        session.add(project)
        await session.flush()
        version = Version(
            project_id=project.id, version_tag="v1",
            upload_path=str(upload), total_files=0, total_lines=0,
        )
        session.add(version)
        await session.flush()
        task = ScanTask(version_id=version.id)
        session.add(task)
        await session.flush()
        await session.commit()

        await ScanOrchestrator().run_scan(task.id, session)
        await session.commit()

        yield session, task.id

    await engine.dispose()


class TestReportRenderers:

    @pytest.mark.asyncio
    async def test_collect_report_data(self, session_with_scan) -> None:
        session, scan_id = session_with_scan
        data = await collect_report_data(scan_id, session)
        assert "scan" in data or "task" in data or "overall_score" in str(data)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_markdown_renderer(self, session_with_scan) -> None:
        session, scan_id = session_with_scan
        data = await collect_report_data(scan_id, session)
        text = render_markdown(data)
        assert isinstance(text, str)
        assert len(text) > 100
        assert "#" in text  # markdown heading

    @pytest.mark.asyncio
    async def test_html_renderer(self, session_with_scan) -> None:
        session, scan_id = session_with_scan
        data = await collect_report_data(scan_id, session)
        text = render_html(data)
        assert "<html" in text.lower() or "<!doctype" in text.lower()

    @pytest.mark.asyncio
    async def test_generate_report_md(self, session_with_scan) -> None:
        session, scan_id = session_with_scan
        path = await generate_report(scan_id, "md", session)
        assert path.exists()
        assert path.suffix == ".md"

    @pytest.mark.asyncio
    async def test_generate_report_html(self, session_with_scan) -> None:
        session, scan_id = session_with_scan
        path = await generate_report(scan_id, "html", session)
        assert path.exists()
        assert path.suffix == ".html"
