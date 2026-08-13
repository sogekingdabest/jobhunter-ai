"""Direct route tests for matching error translation and contracts."""

from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.matching.api.routes import (
    create_match_assessment,
    get_match_assessment,
    get_service,
)
from jobhunter.matching.api.schemas import MatchAssessmentInput
from jobhunter.matching.application.service import MatchingService
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer
from tests.matching.test_service import service


@pytest.mark.asyncio
async def test_routes_create_and_get_assessment() -> None:
    candidate, offer = make_profile(), make_offer()
    matching = service(candidate, offer)
    payload = MatchAssessmentInput(
        candidate_profile_id=candidate.id,
        job_offer_id=offer.id,
    )

    created = await create_match_assessment(payload, matching)
    fetched = await get_match_assessment(created.id, matching)

    assert fetched == created
    assert fetched.dimensions[0].evidence[0].candidate_fact_ids


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("candidate_exists", "offer_exists", "detail"),
    [
        (False, True, "candidate_profile_not_found"),
        (True, False, "job_offer_not_found"),
    ],
)
async def test_create_route_translates_missing_inputs(
    candidate_exists: bool, offer_exists: bool, detail: str
) -> None:
    candidate, offer = make_profile(), make_offer()
    matching = service(candidate if candidate_exists else None, offer if offer_exists else None)
    payload = MatchAssessmentInput(candidate_profile_id=candidate.id, job_offer_id=offer.id)

    with pytest.raises(HTTPException) as captured:
        await create_match_assessment(payload, matching)

    assert captured.value.status_code == status.HTTP_404_NOT_FOUND
    assert captured.value.detail == detail


@pytest.mark.asyncio
async def test_get_route_translates_missing_assessment() -> None:
    with pytest.raises(HTTPException) as captured:
        await get_match_assessment(uuid4(), service(None, None))

    assert captured.value.status_code == status.HTTP_404_NOT_FOUND
    assert captured.value.detail == "match_assessment_not_found"


def test_input_contract_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MatchAssessmentInput.model_validate(
            {"candidate_profile_id": str(uuid4()), "job_offer_id": str(uuid4()), "extra": True}
        )


def test_dependency_wires_sqlalchemy_adapters() -> None:
    matching = get_service(cast(AsyncSession, object()))

    assert isinstance(matching, MatchingService)
