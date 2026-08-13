"""Persistence boundary for normalized job offers."""

from typing import Protocol
from uuid import UUID

from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSpan
from jobhunter.jobs.domain.offers import JobOffer


class JobOfferRepositoryDuplicateError(ValueError):
    """Adapter-neutral uniqueness conflict."""


class JobOfferRepository(Protocol):
    async def add(
        self,
        offer: JobOffer,
        evidence_source: EvidenceSource,
        evidence_spans: tuple[EvidenceSpan, ...],
    ) -> JobOffer: ...

    async def get(self, offer_id: UUID) -> JobOffer | None: ...

    async def get_by_fingerprint(self, fingerprint: str) -> JobOffer | None: ...
