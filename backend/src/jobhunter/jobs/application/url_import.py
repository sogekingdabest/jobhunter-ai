"""Two-step URL preview and grounded import orchestration."""

from jobhunter.ai.contracts.job_offers import JobOfferNormalizationOutput
from jobhunter.jobs.application.errors import JobUrlContentChangedError
from jobhunter.jobs.application.normalization import ManualJobOfferService
from jobhunter.jobs.domain.acquisition import FetchedJobContent
from jobhunter.jobs.domain.offers import JobOffer, JobSource
from jobhunter.jobs.ports.url_fetcher import JobUrlFetcher


class UrlJobOfferService:
    """Acquire URL content safely before delegating normalization validation."""

    def __init__(self, fetcher: JobUrlFetcher, normalizer: ManualJobOfferService) -> None:
        self._fetcher = fetcher
        self._normalizer = normalizer

    async def preview(self, url: str) -> FetchedJobContent:
        return await self._fetcher.fetch(url)

    async def import_normalized(
        self,
        url: str,
        expected_content_fingerprint: str,
        normalization: JobOfferNormalizationOutput,
    ) -> JobOffer:
        content = await self._fetcher.fetch(url)
        if content.content_fingerprint != expected_content_fingerprint:
            raise JobUrlContentChangedError
        return await self._normalizer.import_normalized(
            content.raw_text,
            normalization,
            source=JobSource.URL,
            source_url=content.requested_url,
            canonical_url=content.canonical_url,
        )
