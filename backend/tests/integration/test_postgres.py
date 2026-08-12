"""PostgreSQL session and Alembic migration integration tests."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from jobhunter.infrastructure.database.session import Database

pytestmark = pytest.mark.integration


def get_test_database_url() -> str:
    url = os.getenv("JOBHUNTER_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("JOBHUNTER_TEST_DATABASE_URL is not configured")
    return url


def alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).parents[2]
    configuration = Config(backend_root / "alembic.ini")
    configuration.attributes["database_url"] = database_url
    return configuration


def test_migrations_upgrade_and_downgrade() -> None:
    configuration = alembic_config(get_test_database_url())

    command.downgrade(configuration, "base")
    try:
        command.upgrade(configuration, "head")
        command.current(configuration, check_heads=True)
        command.downgrade(configuration, "base")
    finally:
        command.upgrade(configuration, "head")


@pytest.mark.asyncio
async def test_async_session_executes_query() -> None:
    database = Database(get_test_database_url())

    try:
        async with database.session() as session:
            result = await session.scalar(text("SELECT 1"))
    finally:
        await database.dispose()

    assert result == 1
