"""Direct route and schema tests for manual offers."""

from copy import deepcopy
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from jobhunter.ai.contracts.job_offers import JobOfferNormalizationOutput
from jobhunter.config import Settings
from jobhunter.jobs.api.routes import (
    delete_job_offer,
    get_job_offer,
    get_url_service,
    import_job_offer_url,
    import_manual_job_offer,
    preview_job_offer_url,
)
from jobhunter.jobs.api.schemas import JobUrlImportInput, JobUrlPreviewInput, ManualJobOfferInput
from jobhunter.jobs.application.errors import (
    DuplicateJobOfferError,
    InvalidJobUrlContentError,
    JobUrlContentChangedError,
    JobUrlFetchError,
    UngroundedJobNormalizationError,
    UnsafeJobUrlError,
)
from jobhunter.jobs.application.normalization import ManualJobOfferService, job_content_fingerprint
from jobhunter.jobs.application.url_import import UrlJobOfferService
from jobhunter.jobs.domain.acquisition import FetchedJobContent
from jobhunter.jobs.domain.offers import JobOffer
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
async def test_delete_route_removes_offer_and_translates_missing_error() -> None:
    service = ManualJobOfferService(InMemoryJobOfferRepository())
    created = await import_manual_job_offer(request_payload(), service)

    response = await delete_job_offer(created.id, service)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    with pytest.raises(HTTPException) as missing:
        await delete_job_offer(created.id, service)
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


class StubUrlService:
    def __init__(
        self,
        *,
        content: FetchedJobContent | None = None,
        offer: JobOffer | None = None,
        error: Exception | None = None,
    ) -> None:
        self.content = content
        self.offer = offer
        self.error = error

    async def preview(self, url: str) -> FetchedJobContent:
        del url
        if self.error is not None:
            raise self.error
        assert self.content is not None
        return self.content

    async def import_normalized(self, *args: object) -> JobOffer:
        del args
        if self.error is not None:
            raise self.error
        assert self.offer is not None
        return self.offer


def url_content() -> FetchedJobContent:
    return FetchedJobContent(
        requested_url="https://jobs.example.com/job",
        final_url="https://jobs.example.com/job",
        canonical_url="https://jobs.example.com/job",
        raw_text=JOB_TEXT,
        content_fingerprint=job_content_fingerprint(JOB_TEXT),
        media_type="text/plain",
    )


def url_import_payload() -> JobUrlImportInput:
    return JobUrlImportInput.model_validate(
        {
            "url": "https://jobs.example.com/job",
            "expected_content_fingerprint": job_content_fingerprint(JOB_TEXT),
            "normalization": normalization_payload(),
        }
    )


@pytest.mark.asyncio
async def test_url_routes_return_preview_and_imported_offer() -> None:
    content = url_content()
    offer = await ManualJobOfferService(InMemoryJobOfferRepository()).import_normalized(
        JOB_TEXT, request_payload().normalization
    )

    preview = await preview_job_offer_url(
        JobUrlPreviewInput(url=content.requested_url),
        cast(UrlJobOfferService, StubUrlService(content=content)),
    )
    imported = await import_job_offer_url(
        url_import_payload(),
        cast(UrlJobOfferService, StubUrlService(offer=offer)),
    )

    assert preview.raw_text == JOB_TEXT
    assert imported.id == offer.id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status", "detail"),
    [
        (UnsafeJobUrlError(), status.HTTP_422_UNPROCESSABLE_CONTENT, "unsafe_job_url"),
        (
            InvalidJobUrlContentError("unsupported_job_url_content_type"),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "unsupported_job_url_content_type",
        ),
        (JobUrlFetchError(), status.HTTP_502_BAD_GATEWAY, "job_url_fetch_failed"),
    ],
)
async def test_preview_url_route_translates_safe_errors(
    error: Exception, expected_status: int, detail: str
) -> None:
    with pytest.raises(HTTPException) as captured:
        await preview_job_offer_url(
            JobUrlPreviewInput(url="https://jobs.example.com"),
            cast(UrlJobOfferService, StubUrlService(error=error)),
        )
    assert captured.value.status_code == expected_status
    assert captured.value.detail == detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status", "detail"),
    [
        (UnsafeJobUrlError(), status.HTTP_422_UNPROCESSABLE_CONTENT, "unsafe_job_url"),
        (
            InvalidJobUrlContentError("job_url_content_too_large"),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "job_url_content_too_large",
        ),
        (JobUrlFetchError(), status.HTTP_502_BAD_GATEWAY, "job_url_fetch_failed"),
        (JobUrlContentChangedError(), status.HTTP_409_CONFLICT, "job_url_content_changed"),
        (DuplicateJobOfferError(), status.HTTP_409_CONFLICT, "duplicate_job_offer"),
        (
            UngroundedJobNormalizationError(),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ungrounded_job_normalization",
        ),
        (
            ValueError("invalid_url_offer"),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_url_offer",
        ),
    ],
)
async def test_import_url_route_translates_safe_errors(
    error: Exception, expected_status: int, detail: str
) -> None:
    with pytest.raises(HTTPException) as captured:
        await import_job_offer_url(
            url_import_payload(),
            cast(UrlJobOfferService, StubUrlService(error=error)),
        )
    assert captured.value.status_code == expected_status
    assert captured.value.detail == detail


def test_url_input_contracts_are_strict_and_bounded() -> None:
    with pytest.raises(ValidationError):
        JobUrlPreviewInput(url="x" * 2_049)
    with pytest.raises(ValidationError):
        JobUrlImportInput.model_validate(
            {
                "url": "https://jobs.example.com",
                "expected_content_fingerprint": "invalid",
                "normalization": normalization_payload(),
            }
        )


def test_url_service_dependency_uses_bounded_settings() -> None:
    app = FastAPI()
    app.state.settings = Settings(_env_file=None)
    request = Request({"type": "http", "app": app})

    service = get_url_service(request, cast(AsyncSession, object()))

    assert isinstance(service, UrlJobOfferService)
