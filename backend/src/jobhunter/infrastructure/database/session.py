"""Async SQLAlchemy engine and session lifecycle."""

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if sys.platform == "win32":  # pragma: no cover - platform-specific event loop policy
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Database:
    """Own the database engine and create short-lived application sessions."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(database_url, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield one session without imposing transaction commit policy."""

        async with self.session_factory() as session:
            yield session

    async def dispose(self) -> None:
        """Release pooled connections during application shutdown."""

        await self.engine.dispose()
