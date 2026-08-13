"""Repository integration tests independent of the HTTP execution thread."""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from jobhunter.candidate.infrastructure.database.repository import (
    SqlAlchemyCandidateProfileRepository,
)
from jobhunter.infrastructure.database.session import Database
from tests.candidate.factories import make_profile

pytestmark = pytest.mark.integration


def get_test_database_url() -> str:
    url = os.getenv("JOBHUNTER_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("JOBHUNTER_TEST_DATABASE_URL is not configured")
    return url


def migrate(database_url: str) -> None:
    backend_root = Path(__file__).parents[2]
    configuration = Config(backend_root / "alembic.ini")
    configuration.attributes["database_url"] = database_url
    command.upgrade(configuration, "head")


def test_repository_manages_full_aggregate() -> None:
    database_url = get_test_database_url()
    migrate(database_url)

    asyncio.run(_exercise_repository(database_url))


async def _exercise_repository(database_url: str) -> None:
    database = Database(database_url)
    profile = make_profile()
    try:
        async with database.session() as session:
            repository = SqlAlchemyCandidateProfileRepository(session)
            stored = await repository.add(profile)
            assert stored.id == profile.id
            assert stored.work_experiences == profile.work_experiences

            replacement = make_profile(profile_id=profile.id, source_id=uuid4())
            replaced = await repository.replace(replacement)
            assert replaced is not None
            assert replaced.evidence_source_id == replacement.evidence_source_id

            assert await repository.delete(profile.id)
            assert await repository.get(profile.id) is None
            assert await repository.replace(replacement) is None
            assert not await repository.delete(profile.id)
    finally:
        await database.dispose()
