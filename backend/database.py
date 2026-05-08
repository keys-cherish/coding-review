"""
CodeGuard Pro 数据库连接管理

统一的 SQLAlchemy 引擎和 Session 工厂。
同时提供 sync 和 async 两套接口：
- sync 用于启动时的脚本（建表、内置规则入库）
- async 用于 FastAPI 的请求处理
"""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


# ---------- 同步引擎（脚本/初始化使用） ----------
sync_engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=settings.db_echo,
    future=True,
    connect_args={"check_same_thread": False},
)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


# ---------- 异步引擎（API使用） ----------
async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=settings.db_echo,
    future=True,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, autoflush=False
)


@contextmanager
def get_sync_session() -> Iterator[Session]:
    """脚本场景使用的同步 Session 上下文。"""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖注入用的异步 Session。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI Depends 形式的依赖。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_database() -> None:
    """同步建表 - 启动脚本调用。"""
    from backend import models  # 触发模型加载，确保 Base.metadata 完整  # noqa: F401

    Base.metadata.create_all(bind=sync_engine)
