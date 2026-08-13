"""PostgreSQL repository tests for grounded manual job offers."""

import asyncio
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config

from jobhunter.infrastructure.database.session import Database
from jobhunter.jobs.application.normalization import ManualJobOfferService
from jobhunter.jobs.infrastructure.database.repository import SqlAlchemyJobOfferRepository
from jobhunter.jobs.ports.repository import JobOfferRepositoryDuplicateError
from tests.jobs.factories import JOB_TEXT, make_normalization

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


def test_repository_round_trips_offer_and_enforces_deduplication() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    asyncio.run(_exercise_repository(database_url))


async def _exercise_repository(database_url: str) -> None:
    database = Database(database_url)
    try:
        async with database.session() as session:
            repository = SqlAlchemyJobOfferRepository(session)
            service = ManualJobOfferService(repository)
            raw_text = f"{JOB_TEXT}\nImport reference: {uuid4()}"
            offer = await service.import_normalized(raw_text, make_normalization())
            assert await repository.get(offer.id) == offer
            assert await repository.get_by_fingerprint(offer.content_fingerprint) == offer
            assert await repository.get_by_fingerprint("f" * 64) is None
            assert await repository.get(UUID(int=0)) is None

        async with database.session() as session:
            duplicate_repository = SqlAlchemyJobOfferRepository(session)
            grounded = service._ground(raw_text, make_normalization(), offer.content_fingerprint)
            with pytest.raises(JobOfferRepositoryDuplicateError):
                await duplicate_repository.add(
                    grounded.offer,
                    grounded.evidence_source,
                    grounded.evidence_spans,
                )
    finally:
        await database.dispose()
