"""共享 pytest fixtures。"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """测试 fixtures 根目录。"""
    return FIXTURES


@pytest.fixture(scope="session")
def py_fixture_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "python"


@pytest.fixture(scope="session")
def java_fixture_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "java"
