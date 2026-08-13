"""PostgreSQL integration for grounded extraction and review persistence."""

import asyncio
import os
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config

from jobhunter.candidate.domain.facts import ProposalReviewStatus
from jobhunter.candidate.infrastructure.database.fact_extraction_repository import (
    SqlAlchemyCandidateFactExtractionRepository,
)
from jobhunter.candidate.ports.fact_extraction_repository import (
    CandidateFactExtractionConflictError,
)
from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSourceType, EvidenceSpan
from jobhunter.documents.infrastructure.database.models import SourceDocumentModel
from jobhunter.infrastructure.database.session import Database
from tests.candidate.fact_extraction_factories import NOW, make_extraction

pytestmark = pytest.mark.integration


def get_test_database_url() -> str:
    url = os.getenv("JOBHUNTER_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("JOBHUNTER_TEST_DATABASE_URL is not configured")
    return url


def migrate(database_url: str) -> None:
    configuration = Config(Path(__file__).parents[2] / "alembic.ini")
    configuration.attributes["database_url"] = database_url
    command.upgrade(configuration, "head")


def test_repository_persists_grounded_extraction_and_review() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    asyncio.run(_exercise_repository(database_url))


async def _exercise_repository(database_url: str) -> None:
    database = Database(database_url)
    extraction = replace(make_extraction(), warnings=("Dates were not explicit.",))
    proposal = extraction.proposals[0]
    evidence_source = EvidenceSource(
        extraction.evidence_source_id,
        EvidenceSourceType.DOCUMENT,
        extraction.source_document_id,
        NOW,
    )
    evidence_span = EvidenceSpan(
        proposal.evidence_span_id,
        extraction.evidence_source_id,
        proposal.evidence_quote,
        sha256(proposal.evidence_quote.encode()).hexdigest(),
        proposal.start_offset,
        proposal.end_offset,
        proposal.page_number,
        NOW,
    )
    try:
        async with database.session() as session:
            session.add(
                SourceDocumentModel(
                    id=extraction.source_document_id,
                    storage_key=f"documents/{extraction.source_document_id.hex}",
                    media_type="text/plain",
                    size_bytes=6,
                    sha256=sha256(b"Python").hexdigest(),
                    status="processed",
                    parser_version="test-v1",
                )
            )
            await session.commit()

        async with database.session() as session:
            repository = SqlAlchemyCandidateFactExtractionRepository(session)
            stored = await repository.add(extraction, evidence_source, (evidence_span,))
            assert stored.proposals[0].evidence_quote == "Python"
            assert stored.proposals[0].page_number == 1
            assert stored.warnings == ("Dates were not explicit.",)

            reviewed = stored.review(proposal.id, ProposalReviewStatus.ACCEPTED, reviewed_at=NOW)
            persisted = await repository.replace(reviewed)
            assert persisted == reviewed
            assert await repository.get(extraction.id) == reviewed
            stale = extraction.review(proposal.id, ProposalReviewStatus.REJECTED, reviewed_at=NOW)
            with pytest.raises(CandidateFactExtractionConflictError):
                await repository.replace(stale)
            assert await repository.get(uuid4()) is None
            assert await repository.replace(make_extraction()) is None
    finally:
        await database.dispose()
