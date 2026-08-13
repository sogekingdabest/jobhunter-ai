"""REST contracts for reviewing grounded candidate-fact proposals."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from jobhunter.candidate.domain.facts import (
    CandidateFactType,
    ExtractionStatus,
    ProposalReviewStatus,
)


class FactExtractionSchema(BaseModel):
    """Strict shared response and input behavior."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ProposalReviewInput(FactExtractionSchema):
    """One irreversible user decision."""

    decision: Literal[ProposalReviewStatus.ACCEPTED, ProposalReviewStatus.REJECTED]


class CandidateFactProposalResponse(FactExtractionSchema):
    """A proposal together with the exact evidence needed for review."""

    id: UUID
    extraction_id: UUID
    evidence_span_id: UUID
    evidence_quote: str
    start_offset: int
    end_offset: int
    page_number: int | None
    fact_type: CandidateFactType
    value: str
    confidence: float
    review_status: ProposalReviewStatus
    reviewed_at: datetime | None


class CandidateFactExtractionResponse(FactExtractionSchema):
    """Complete review queue for one CV extraction attempt."""

    id: UUID
    source_document_id: UUID
    evidence_source_id: UUID
    contract_version: str
    provider: str
    model: str
    warnings: tuple[str, ...]
    proposals: tuple[CandidateFactProposalResponse, ...]
    status: ExtractionStatus
    created_at: datetime
    revision: int
    completed_at: datetime | None
