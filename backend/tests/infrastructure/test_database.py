"""Unit tests for shared database infrastructure."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.infrastructure.database.base import NAMING_CONVENTION, Base
from jobhunter.infrastructure.database.session import Database


def test_base_uses_stable_constraint_names() -> None:
    assert Base.metadata.naming_convention == NAMING_CONVENTION


@pytest.mark.asyncio
async def test_database_manages_session_and_engine_lifecycle() -> None:
    engine = MagicMock()
    engine.dispose = AsyncMock()
    session = MagicMock()
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    session_factory = MagicMock(return_value=session_context)

    with (
        patch(
            "jobhunter.infrastructure.database.session.create_async_engine",
            return_value=engine,
        ) as create_engine,
        patch(
            "jobhunter.infrastructure.database.session.async_sessionmaker",
            return_value=session_factory,
        ) as create_session_factory,
    ):
        database = Database("postgresql+psycopg://user:password@database/example")

        async with database.session() as opened_session:
            assert opened_session is session

        await database.dispose()

    create_engine.assert_called_once_with(
        "postgresql+psycopg://user:password@database/example",
        pool_pre_ping=True,
    )
    create_session_factory.assert_called_once_with(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session_context.__aexit__.assert_awaited_once()
    engine.dispose.assert_awaited_once()
