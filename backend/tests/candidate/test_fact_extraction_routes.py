"""Route and schema tests for candidate fact review."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.candidate.api.fact_extraction_routes import (
    get_candidate_fact_extraction,
    get_service,
    get_session,
    review_candidate_fact_proposal,
)
from jobhunter.candidate.api.fact_extraction_schemas import ProposalReviewInput
from jobhunter.candidate.application.fact_extraction import CandidateFactReviewService
from jobhunter.candidate.domain.facts import ProposalReviewStatus
from tests.candidate.fact_extraction_factories import make_extraction
from tests.candidate.test_fact_extraction_service import InMemoryFactExtractionRepository


@pytest.mark.asyncio
async def test_routes_return_and_review_grounded_proposals() -> None:
    repository = InMemoryFactExtractionRepository()
    extraction = make_extraction()
    repository.extractions[extraction.id] = extraction
    service = CandidateFactReviewService(repository)

    response = await get_candidate_fact_extraction(extraction.id, service)
    reviewed = await review_candidate_fact_proposal(
        extraction.id,
        extraction.proposals[0].id,
        ProposalReviewInput(decision=ProposalReviewStatus.ACCEPTED),
        service,
    )

    assert response.proposals[0].evidence_quote == "Python"
    assert reviewed.proposals[0].review_status is ProposalReviewStatus.ACCEPTED


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["get", "review"])
async def test_routes_report_missing_extraction(operation: str) -> None:
    service = CandidateFactReviewService(InMemoryFactExtractionRepository())
    extraction_id = uuid4()

    if operation == "get":
        coroutine = get_candidate_fact_extraction(extraction_id, service)
    else:
        coroutine = review_candidate_fact_proposal(
            extraction_id,
            uuid4(),
            ProposalReviewInput(decision=ProposalReviewStatus.REJECTED),
            service,
        )
    with pytest.raises(HTTPException) as captured:
        await coroutine
    assert captured.value.status_code == status.HTTP_404_NOT_FOUND
    assert captured.value.detail == "candidate_fact_extraction_not_found"


@pytest.mark.asyncio
async def test_routes_report_missing_or_already_reviewed_proposal() -> None:
    repository = InMemoryFactExtractionRepository()
    extraction = make_extraction()
    repository.extractions[extraction.id] = extraction
    service = CandidateFactReviewService(repository)
    payload = ProposalReviewInput(decision=ProposalReviewStatus.ACCEPTED)

    with pytest.raises(HTTPException) as missing:
        await review_candidate_fact_proposal(extraction.id, uuid4(), payload, service)
    await review_candidate_fact_proposal(
        extraction.id, extraction.proposals[0].id, payload, service
    )
    with pytest.raises(HTTPException) as conflict:
        await review_candidate_fact_proposal(
            extraction.id, extraction.proposals[0].id, payload, service
        )

    assert missing.value.detail == "candidate_fact_proposal_not_found"
    assert conflict.value.status_code == status.HTTP_409_CONFLICT
    assert conflict.value.detail == "candidate_fact_already_reviewed"


@pytest.mark.asyncio
async def test_route_reports_concurrent_review_conflict() -> None:
    repository = InMemoryFactExtractionRepository()
    extraction = make_extraction()
    repository.extractions[extraction.id] = extraction
    repository.force_conflict = True
    service = CandidateFactReviewService(repository)

    with pytest.raises(HTTPException) as conflict:
        await review_candidate_fact_proposal(
            extraction.id,
            extraction.proposals[0].id,
            ProposalReviewInput(decision=ProposalReviewStatus.ACCEPTED),
            service,
        )
    assert conflict.value.status_code == status.HTTP_409_CONFLICT
    assert conflict.value.detail == "candidate_fact_extraction_changed"


def test_review_schema_rejects_pending_decision() -> None:
    with pytest.raises(ValidationError):
        ProposalReviewInput(decision="needs_review")


def test_service_dependency_builds_sqlalchemy_adapter() -> None:
    service = get_service(cast(AsyncSession, object()))
    assert isinstance(service, CandidateFactReviewService)


@pytest.mark.asyncio
async def test_session_dependency_uses_application_database() -> None:
    sentinel = cast(AsyncSession, object())

    class FakeDatabase:
        @asynccontextmanager
        async def session(self) -> AsyncIterator[AsyncSession]:
            yield sentinel

    request = cast(
        Request,
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=FakeDatabase()))),
    )

    sessions = [session async for session in get_session(request)]
    assert sessions == [sentinel]
