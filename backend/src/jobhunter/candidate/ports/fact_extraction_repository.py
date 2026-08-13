"""Persistence port for grounded candidate-fact extraction and review."""

from typing import Protocol
from uuid import UUID

from jobhunter.candidate.domain.facts import CandidateFactExtraction
from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSpan


class CandidateFactExtractionConflictError(Exception):
    """Raised when persisted review state changed since it was read."""


class CandidateFactExtractionRepository(Protocol):  # pragma: no cover - structural typing
    """Persist an extraction and its document evidence as one transaction."""

    async def add(
        self,
        extraction: CandidateFactExtraction,
        evidence_source: EvidenceSource,
        evidence_spans: tuple[EvidenceSpan, ...],
    ) -> CandidateFactExtraction:
        """Add a new grounded extraction."""

    async def get(self, extraction_id: UUID) -> CandidateFactExtraction | None:
        """Return one extraction with all proposals."""

    async def replace(self, extraction: CandidateFactExtraction) -> CandidateFactExtraction | None:
        """Persist review state for an existing extraction."""
