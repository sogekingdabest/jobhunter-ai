"""Application orchestration tests for two-step URL imports."""

from uuid import UUID

import pytest

from jobhunter.jobs.application.errors import JobUrlContentChangedError
from jobhunter.jobs.application.normalization import ManualJobOfferService, job_content_fingerprint
from jobhunter.jobs.application.url_import import UrlJobOfferService
from jobhunter.jobs.domain.acquisition import FetchedJobContent
from jobhunter.jobs.domain.offers import JobOffer, JobSource
from tests.jobs.factories import JOB_TEXT, make_normalization
from tests.jobs.test_normalization import InMemoryJobOfferRepository


class FakeJobUrlFetcher:
    def __init__(self, content: FetchedJobContent) -> None:
        self.content = content
        self.urls: list[str] = []

    async def fetch(self, url: str) -> FetchedJobContent:
        self.urls.append(url)
        return self.content


def fetched_content(text: str = JOB_TEXT) -> FetchedJobContent:
    return FetchedJobContent(
        requested_url="https://jobs.example.com/job",
        final_url="https://careers.example.com/jobs/42",
        canonical_url="https://careers.example.com/jobs/backend",
        raw_text=text,
        content_fingerprint=job_content_fingerprint(text),
        media_type="text/html",
    )


def make_service() -> tuple[UrlJobOfferService, FakeJobUrlFetcher, dict[UUID, JobOffer]]:
    repository = InMemoryJobOfferRepository()
    fetcher = FakeJobUrlFetcher(fetched_content())
    service = UrlJobOfferService(fetcher, ManualJobOfferService(repository))
    return service, fetcher, repository.offers


@pytest.mark.asyncio
async def test_preview_returns_unpersisted_extracted_content() -> None:
    service, fetcher, offers = make_service()

    result = await service.preview("https://jobs.example.com/job")

    assert result == fetcher.content
    assert fetcher.urls == ["https://jobs.example.com/job"]
    assert offers == {}


@pytest.mark.asyncio
async def test_import_refetches_expected_content_and_preserves_url_provenance() -> None:
    service, fetcher, offers = make_service()

    offer = await service.import_normalized(
        "https://jobs.example.com/job",
        fetcher.content.content_fingerprint,
        make_normalization(),
    )

    assert offer.source is JobSource.URL
    assert offer.source_url == fetcher.content.requested_url
    assert offer.canonical_url == fetcher.content.canonical_url
    assert offers == {offer.id: offer}


@pytest.mark.asyncio
async def test_import_rejects_changed_content_before_persistence() -> None:
    service, _, offers = make_service()

    with pytest.raises(JobUrlContentChangedError):
        await service.import_normalized(
            "https://jobs.example.com/job",
            "0" * 64,
            make_normalization(),
        )

    assert offers == {}
