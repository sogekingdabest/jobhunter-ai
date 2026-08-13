"""Candidate-owned fact vocabulary and human-review workflow."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from jobhunter.candidate.domain.common import ensure_unique_ids, require_text


class CandidateFactType(StrEnum):
    """Kinds of profile facts that may be proposed for the master CV."""

    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    PROJECT = "project"
    CERTIFICATION = "certification"
    COMPETENCY = "competency"
    LANGUAGE = "language"


class ProposalReviewStatus(StrEnum):
    """Human decision for an extracted fact proposal."""

    NEEDS_REVIEW = "needs_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ExtractionStatus(StrEnum):
    """Review state for a complete extraction attempt."""

    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"


@dataclass(frozen=True, slots=True)
class CandidateFactProposal:
    """Grounded model output that cannot become candidate truth without review."""

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
    review_status: ProposalReviewStatus = ProposalReviewStatus.NEEDS_REVIEW
    reviewed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_text(self.value, "candidate_fact_value")
        require_text(self.evidence_quote, "candidate_fact_evidence")
        if self.start_offset < 0 or self.end_offset <= self.start_offset:
            raise ValueError("invalid_candidate_fact_evidence_offsets")
        if self.page_number is not None and self.page_number <= 0:
            raise ValueError("invalid_candidate_fact_evidence_page")
        if not 0 <= self.confidence <= 1:
            raise ValueError("invalid_candidate_fact_confidence")
        is_reviewed = self.review_status is not ProposalReviewStatus.NEEDS_REVIEW
        if is_reviewed != (self.reviewed_at is not None):
            raise ValueError("invalid_candidate_fact_review_state")

    def review(
        self, decision: ProposalReviewStatus, *, reviewed_at: datetime
    ) -> "CandidateFactProposal":
        """Apply the proposal's one-way human decision."""

        if self.review_status is not ProposalReviewStatus.NEEDS_REVIEW:
            raise ValueError("candidate_fact_already_reviewed")
        if decision is ProposalReviewStatus.NEEDS_REVIEW:
            raise ValueError("invalid_candidate_fact_decision")
        return replace(self, review_status=decision, reviewed_at=reviewed_at)


@dataclass(frozen=True, slots=True)
class CandidateFactExtraction:
    """One immutable model attempt plus mutable-by-replacement review decisions."""

    id: UUID
    source_document_id: UUID
    evidence_source_id: UUID
    contract_version: str
    provider: str
    model: str
    warnings: tuple[str, ...]
    proposals: tuple[CandidateFactProposal, ...]
    status: ExtractionStatus
    created_at: datetime
    revision: int = 0
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        require_text(self.contract_version, "contract_version")
        require_text(self.provider, "provider")
        require_text(self.model, "model")
        if any(not warning.strip() for warning in self.warnings):
            raise ValueError("empty_candidate_fact_warning")
        if self.revision < 0:
            raise ValueError("invalid_candidate_fact_extraction_revision")
        ensure_unique_ids(proposal.id for proposal in self.proposals)
        ensure_unique_ids(proposal.evidence_span_id for proposal in self.proposals)
        if any(proposal.extraction_id != self.id for proposal in self.proposals):
            raise ValueError("foreign_candidate_fact_proposal")
        has_pending = any(
            proposal.review_status is ProposalReviewStatus.NEEDS_REVIEW
            for proposal in self.proposals
        )
        if (self.status is ExtractionStatus.NEEDS_REVIEW) != has_pending:
            raise ValueError("invalid_candidate_fact_extraction_status")
        if (self.status is ExtractionStatus.REVIEWED) != (self.completed_at is not None):
            raise ValueError("invalid_candidate_fact_completion_state")

    def review(
        self,
        proposal_id: UUID,
        decision: ProposalReviewStatus,
        *,
        reviewed_at: datetime,
    ) -> "CandidateFactExtraction":
        """Review one owned proposal and complete the extraction when none remain."""

        found = False
        proposals: list[CandidateFactProposal] = []
        for current in self.proposals:
            proposal = current
            if current.id == proposal_id:
                found = True
                proposal = current.review(decision, reviewed_at=reviewed_at)
            proposals.append(proposal)
        if not found:
            raise ValueError("candidate_fact_proposal_not_found")

        remaining = any(
            proposal.review_status is ProposalReviewStatus.NEEDS_REVIEW for proposal in proposals
        )
        return replace(
            self,
            proposals=tuple(proposals),
            status=ExtractionStatus.NEEDS_REVIEW if remaining else ExtractionStatus.REVIEWED,
            revision=self.revision + 1,
            completed_at=None if remaining else reviewed_at,
        )
