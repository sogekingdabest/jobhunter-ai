"""Fictional helpers for candidate fact extraction tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from jobhunter.candidate.domain.facts import (
    CandidateFactExtraction,
    CandidateFactProposal,
    CandidateFactType,
    ExtractionStatus,
    ProposalReviewStatus,
)

NOW = datetime(2026, 8, 13, 10, tzinfo=UTC)


def make_proposal(
    *,
    extraction_id: UUID,
    proposal_id: UUID | None = None,
    evidence_span_id: UUID | None = None,
    review_status: ProposalReviewStatus = ProposalReviewStatus.NEEDS_REVIEW,
    reviewed_at: datetime | None = None,
) -> CandidateFactProposal:
    return CandidateFactProposal(
        id=proposal_id or uuid4(),
        extraction_id=extraction_id,
        evidence_span_id=evidence_span_id or uuid4(),
        evidence_quote="Python",
        start_offset=0,
        end_offset=6,
        page_number=1,
        fact_type=CandidateFactType.COMPETENCY,
        value="Python",
        confidence=0.98,
        review_status=review_status,
        reviewed_at=reviewed_at,
    )


def make_extraction(
    *,
    extraction_id: UUID | None = None,
    proposal_id: UUID | None = None,
) -> CandidateFactExtraction:
    resolved_id = extraction_id or uuid4()
    return CandidateFactExtraction(
        id=resolved_id,
        source_document_id=uuid4(),
        evidence_source_id=uuid4(),
        contract_version="1.0",
        provider="fake",
        model="fake-v1",
        warnings=(),
        proposals=(make_proposal(extraction_id=resolved_id, proposal_id=proposal_id),),
        status=ExtractionStatus.NEEDS_REVIEW,
        created_at=NOW,
    )
