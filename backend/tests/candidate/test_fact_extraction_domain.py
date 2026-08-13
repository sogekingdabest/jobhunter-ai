"""Domain invariants for extracted candidate facts and their review."""

from collections.abc import Callable
from dataclasses import replace
from uuid import uuid4

import pytest

from jobhunter.candidate.domain.facts import (
    CandidateFactExtraction,
    ExtractionStatus,
    ProposalReviewStatus,
)
from tests.candidate.fact_extraction_factories import NOW, make_extraction, make_proposal


def test_review_completes_extraction_after_last_decision() -> None:
    extraction = make_extraction()
    proposal = extraction.proposals[0]

    reviewed = extraction.review(proposal.id, ProposalReviewStatus.ACCEPTED, reviewed_at=NOW)

    assert reviewed.status is ExtractionStatus.REVIEWED
    assert reviewed.completed_at == NOW
    assert reviewed.revision == 1
    assert reviewed.proposals[0].review_status is ProposalReviewStatus.ACCEPTED


def test_review_keeps_extraction_pending_until_every_proposal_is_reviewed() -> None:
    extraction = make_extraction()
    second = make_proposal(extraction_id=extraction.id)
    extraction = replace(extraction, proposals=(*extraction.proposals, second))

    reviewed = extraction.review(
        extraction.proposals[0].id, ProposalReviewStatus.REJECTED, reviewed_at=NOW
    )

    assert reviewed.status is ExtractionStatus.NEEDS_REVIEW
    assert reviewed.completed_at is None


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"value": " "}, "candidate_fact_value"),
        ({"evidence_quote": ""}, "candidate_fact_evidence"),
        ({"start_offset": -1}, "invalid_candidate_fact_evidence_offsets"),
        ({"end_offset": 0}, "invalid_candidate_fact_evidence_offsets"),
        ({"page_number": 0}, "invalid_candidate_fact_evidence_page"),
        ({"confidence": -0.1}, "invalid_candidate_fact_confidence"),
        ({"confidence": 1.1}, "invalid_candidate_fact_confidence"),
        (
            {"review_status": ProposalReviewStatus.ACCEPTED},
            "invalid_candidate_fact_review_state",
        ),
        ({"reviewed_at": NOW}, "invalid_candidate_fact_review_state"),
    ],
)
def test_proposal_rejects_invalid_state(changes: dict[str, object], error: str) -> None:
    proposal = make_proposal(extraction_id=uuid4())
    with pytest.raises(ValueError, match=error):
        replace(proposal, **changes)  # type: ignore[arg-type]


def test_proposal_rejects_second_or_pending_review() -> None:
    proposal = make_proposal(extraction_id=uuid4())
    with pytest.raises(ValueError, match="invalid_candidate_fact_decision"):
        proposal.review(ProposalReviewStatus.NEEDS_REVIEW, reviewed_at=NOW)
    reviewed = proposal.review(ProposalReviewStatus.ACCEPTED, reviewed_at=NOW)
    with pytest.raises(ValueError, match="candidate_fact_already_reviewed"):
        reviewed.review(ProposalReviewStatus.REJECTED, reviewed_at=NOW)


@pytest.mark.parametrize(
    ("builder", "error"),
    [
        (lambda item: replace(item, contract_version=""), "contract_version"),
        (lambda item: replace(item, provider=""), "provider"),
        (lambda item: replace(item, model=""), "model"),
        (lambda item: replace(item, warnings=("",)), "empty_candidate_fact_warning"),
        (
            lambda item: replace(item, revision=-1),
            "invalid_candidate_fact_extraction_revision",
        ),
        (
            lambda item: replace(item, proposals=(item.proposals[0], item.proposals[0])),
            "duplicate_entity_id",
        ),
        (
            lambda item: replace(
                item,
                proposals=(
                    item.proposals[0],
                    make_proposal(
                        extraction_id=item.id,
                        evidence_span_id=item.proposals[0].evidence_span_id,
                    ),
                ),
            ),
            "duplicate_entity_id",
        ),
        (
            lambda item: replace(
                item, proposals=(replace(item.proposals[0], extraction_id=uuid4()),)
            ),
            "foreign_candidate_fact_proposal",
        ),
        (
            lambda item: replace(item, status=ExtractionStatus.REVIEWED),
            "invalid_candidate_fact_extraction_status",
        ),
        (
            lambda item: replace(item, completed_at=NOW),
            "invalid_candidate_fact_completion_state",
        ),
    ],
)
def test_extraction_rejects_invalid_state(
    builder: Callable[[CandidateFactExtraction], CandidateFactExtraction], error: str
) -> None:
    extraction = make_extraction()
    with pytest.raises(ValueError, match=error):
        builder(extraction)


def test_extraction_rejects_unknown_proposal() -> None:
    with pytest.raises(ValueError, match="candidate_fact_proposal_not_found"):
        make_extraction().review(uuid4(), ProposalReviewStatus.ACCEPTED, reviewed_at=NOW)
