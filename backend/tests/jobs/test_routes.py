"""Direct route and schema tests for manual offers."""

from copy import deepcopy
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from jobhunter.ai.contracts.job_offers import JobOfferNormalizationOutput
from jobhunter.jobs.api.routes import get_job_offer, import_manual_job_offer
from jobhunter.jobs.api.schemas import ManualJobOfferInput
from jobhunter.jobs.application.normalization import ManualJobOfferService
from tests.jobs.factories import JOB_TEXT, normalization_payload
from tests.jobs.test_normalization import InMemoryJobOfferRepository


def request_payload() -> ManualJobOfferInput:
    return ManualJobOfferInput.model_validate(
        {"raw_text": JOB_TEXT, "normalization": normalization_payload()}
    )


@pytest.mark.asyncio
async def test_routes_import_and_get_grounded_offer() -> None:
    service = ManualJobOfferService(InMemoryJobOfferRepository())
    created = await import_manual_job_offer(request_payload(), service)
    fetched = await get_job_offer(created.id, service)

    assert created.title == "Backend Engineer"
    assert created.requirements[0].original_text == "Python"
    assert fetched == created


@pytest.mark.asyncio
async def test_routes_translate_duplicate_and_missing_errors() -> None:
    service = ManualJobOfferService(InMemoryJobOfferRepository())
    await import_manual_job_offer(request_payload(), service)
    with pytest.raises(HTTPException) as duplicate:
        await import_manual_job_offer(request_payload(), service)
    with pytest.raises(HTTPException) as missing:
        await get_job_offer(uuid4(), service)

    assert duplicate.value.status_code == status.HTTP_409_CONFLICT
    assert duplicate.value.detail == "duplicate_job_offer"
    assert missing.value.status_code == status.HTTP_404_NOT_FOUND
    assert missing.value.detail == "job_offer_not_found"


@pytest.mark.asyncio
async def test_route_rejects_ungrounded_normalization() -> None:
    data = deepcopy(normalization_payload())
    company = cast(dict[str, object], data["company"])
    evidence = cast(dict[str, object], company["evidence"])
    evidence["quote"] = "Fabricated"
    payload = request_payload().model_copy(
        update={"normalization": JobOfferNormalizationOutput.model_validate(data)}
    )

    with pytest.raises(HTTPException) as captured:
        await import_manual_job_offer(payload, ManualJobOfferService(InMemoryJobOfferRepository()))

    assert captured.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert captured.value.detail == "ungrounded_job_normalization"


@pytest.mark.asyncio
async def test_route_translates_domain_validation_error() -> None:
    payload = request_payload().model_copy(update={"raw_text": "   "})

    with pytest.raises(HTTPException) as captured:
        await import_manual_job_offer(payload, ManualJobOfferService(InMemoryJobOfferRepository()))

    assert captured.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert captured.value.detail == "missing_job_offer_text"


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_text": "", "normalization": normalization_payload()},
        {"raw_text": JOB_TEXT, "normalization": normalization_payload(), "extra": True},
    ],
)
def test_manual_input_is_strict_and_bounded(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ManualJobOfferInput.model_validate(payload)


def test_manual_input_preserves_original_source_whitespace() -> None:
    payload = request_payload().model_copy(update={"raw_text": f"  {JOB_TEXT}\n"})

    assert payload.raw_text.startswith("  ")
    assert payload.raw_text.endswith("\n")
