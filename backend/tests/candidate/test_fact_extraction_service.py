"""Application tests for grounding model output and human review."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from jobhunter.ai.application.structured_generation import StructuredGenerationService
from jobhunter.ai.domain.types import FinishReason, JSONObject
from jobhunter.ai.infrastructure.fake import (
    FakeStructuredFixture,
    FakeStructuredLLMProvider,
    InMemoryAIObservabilitySink,
)
from jobhunter.candidate.application.errors import (
    CandidateFactAlreadyReviewedError,
    CandidateFactExtractionNotFoundError,
    CandidateFactProposalNotFoundError,
    CandidateFactReviewConflictError,
    IncompleteCandidateFactExtractionError,
    UngroundedCandidateFactError,
)
from jobhunter.candidate.application.fact_extraction import (
    EXTRACTION_INSTRUCTION,
    CandidateFactExtractionService,
    CandidateFactReviewService,
)
from jobhunter.candidate.domain.facts import (
    CandidateFactExtraction,
    ExtractionStatus,
    ProposalReviewStatus,
)
from jobhunter.candidate.ports.fact_extraction_repository import (
    CandidateFactExtractionConflictError,
)
from jobhunter.documents.domain.entities import EvidenceSource, EvidenceSpan
from jobhunter.documents.domain.parsing import build_parsed_document
from tests.ai.factories import FICTIONAL_SOURCE, make_provider_info, valid_output
from tests.candidate.fact_extraction_factories import NOW, make_extraction


class InMemoryFactExtractionRepository:
    """Capture atomic extraction writes and review replacements."""

    def __init__(self) -> None:
        self.extractions: dict[UUID, CandidateFactExtraction] = {}
        self.evidence_source: EvidenceSource | None = None
        self.evidence_spans: tuple[EvidenceSpan, ...] = ()
        self.force_missing_replace = False
        self.force_conflict = False

    async def add(
        self,
        extraction: CandidateFactExtraction,
        evidence_source: EvidenceSource,
        evidence_spans: tuple[EvidenceSpan, ...],
    ) -> CandidateFactExtraction:
        self.extractions[extraction.id] = extraction
        self.evidence_source = evidence_source
        self.evidence_spans = evidence_spans
        return extraction

    async def get(self, extraction_id: UUID) -> CandidateFactExtraction | None:
        return self.extractions.get(extraction_id)

    async def replace(self, extraction: CandidateFactExtraction) -> CandidateFactExtraction | None:
        if self.force_conflict:
            raise CandidateFactExtractionConflictError
        if self.force_missing_replace or extraction.id not in self.extractions:
            return None
        self.extractions[extraction.id] = extraction
        return extraction


def make_extraction_service(
    output: JSONObject,
    *,
    finish_reason: FinishReason = FinishReason.COMPLETE,
) -> tuple[CandidateFactExtractionService, InMemoryFactExtractionRepository, list[UUID]]:
    ids = [uuid4() for _ in range(10)]
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {ids[0]: FakeStructuredFixture(output=output, finish_reason=finish_reason)},
    )
    generation = StructuredGenerationService(provider, InMemoryAIObservabilitySink())
    repository = InMemoryFactExtractionRepository()
    id_iterator = iter(ids)
    service = CandidateFactExtractionService(
        generation,
        repository,
        id_factory=lambda: next(id_iterator),
        clock=lambda: NOW,
    )
    return service, repository, ids


@pytest.mark.asyncio
async def test_extraction_persists_only_grounded_reviewable_proposals() -> None:
    output = valid_output()
    output["warnings"] = ["Dates were not explicit."]
    service, repository, ids = make_extraction_service(output)
    parsed = build_parsed_document(((FICTIONAL_SOURCE, 3),), parser_version="test-v1")
    document_id = uuid4()

    extraction = await service.extract(document_id, parsed)

    assert extraction.id == ids[1]
    assert extraction.status is ExtractionStatus.NEEDS_REVIEW
    assert extraction.proposals[0].evidence_quote == "Python"
    assert extraction.proposals[0].page_number == parsed.spans[0].page_number
    assert extraction.warnings == ("Dates were not explicit.",)
    assert repository.evidence_source is not None
    assert repository.evidence_source.source_document_id == document_id
    assert repository.evidence_spans[0].quoted_text == "Python"
    assert "untrusted data" in EXTRACTION_INSTRUCTION


@pytest.mark.asyncio
async def test_extraction_deduplicates_identical_proposals() -> None:
    output = valid_output()
    facts = cast(list[object], output["facts"])
    facts.append(deepcopy(facts[0]))
    service, repository, _ = make_extraction_service(output)
    parsed = build_parsed_document(((FICTIONAL_SOURCE, None),), parser_version="test-v1")

    extraction = await service.extract(uuid4(), parsed)

    assert len(extraction.proposals) == 1
    assert len(repository.evidence_spans) == 1


@pytest.mark.asyncio
async def test_empty_extraction_is_completed_without_review() -> None:
    output = cast(JSONObject, {"contract_version": "1.0", "facts": [], "warnings": []})
    service, repository, _ = make_extraction_service(output)
    parsed = build_parsed_document((("No professional facts", None),), parser_version="test-v1")

    extraction = await service.extract(uuid4(), parsed)

    assert extraction.status is ExtractionStatus.REVIEWED
    assert extraction.completed_at == NOW
    assert repository.evidence_spans == ()


@pytest.mark.asyncio
async def test_incomplete_provider_output_is_never_persisted() -> None:
    service, repository, _ = make_extraction_service(
        valid_output(), finish_reason=FinishReason.LENGTH
    )
    parsed = build_parsed_document(((FICTIONAL_SOURCE, None),), parser_version="test-v1")

    with pytest.raises(IncompleteCandidateFactExtractionError):
        await service.extract(uuid4(), parsed)
    assert repository.extractions == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["quote", "bounds", "block", "page"])
async def test_ungrounded_evidence_is_never_persisted(failure: str) -> None:
    output = valid_output()
    fact = cast(dict[str, object], cast(list[object], output["facts"])[0])
    evidence = cast(dict[str, object], fact["evidence"])
    blocks: tuple[tuple[str, int | None], ...] = ((FICTIONAL_SOURCE, 2),)
    if failure == "quote":
        evidence["quote"] = "Django"
    elif failure == "bounds":
        evidence["end_offset"] = 999
    elif failure == "block":
        output = cast(
            JSONObject,
            {
                "contract_version": "1.0",
                "facts": [
                    {
                        "fact_type": "competency",
                        "value": "Python SQL",
                        "evidence": {
                            "quote": "Python\n\nSQL",
                            "start_offset": 0,
                            "end_offset": 11,
                            "page_number": 2,
                        },
                        "confidence": 0.9,
                    }
                ],
                "warnings": [],
            },
        )
        blocks = (("Python", 2), ("SQL", 2))
    else:
        evidence["page_number"] = 4
    service, repository, _ = make_extraction_service(output)
    parsed = build_parsed_document(blocks, parser_version="test-v1")

    with pytest.raises(UngroundedCandidateFactError):
        await service.extract(uuid4(), parsed)
    assert repository.extractions == {}


@pytest.mark.asyncio
async def test_review_service_records_decisions_and_reports_safe_errors() -> None:
    repository = InMemoryFactExtractionRepository()
    extraction = make_extraction()
    repository.extractions[extraction.id] = extraction
    review = CandidateFactReviewService(repository, clock=lambda: NOW)
    proposal_id = extraction.proposals[0].id

    assert await review.get(extraction.id) == extraction
    with pytest.raises(ValueError, match="invalid_candidate_fact_decision"):
        await review.review(extraction.id, proposal_id, ProposalReviewStatus.NEEDS_REVIEW)
    accepted = await review.review(extraction.id, proposal_id, ProposalReviewStatus.ACCEPTED)
    assert accepted.status is ExtractionStatus.REVIEWED

    with pytest.raises(CandidateFactAlreadyReviewedError):
        await review.review(extraction.id, proposal_id, ProposalReviewStatus.REJECTED)
    with pytest.raises(CandidateFactProposalNotFoundError):
        await review.review(extraction.id, uuid4(), ProposalReviewStatus.REJECTED)
    with pytest.raises(CandidateFactExtractionNotFoundError):
        await review.get(uuid4())


@pytest.mark.asyncio
async def test_review_service_handles_concurrent_deletion() -> None:
    repository = InMemoryFactExtractionRepository()
    extraction = make_extraction()
    repository.extractions[extraction.id] = extraction
    repository.force_missing_replace = True
    review = CandidateFactReviewService(
        repository, clock=lambda: datetime(2026, 8, 13, 11, tzinfo=UTC)
    )

    with pytest.raises(CandidateFactExtractionNotFoundError):
        await review.review(
            extraction.id,
            extraction.proposals[0].id,
            ProposalReviewStatus.REJECTED,
        )


@pytest.mark.asyncio
async def test_review_service_translates_concurrent_review_conflict() -> None:
    repository = InMemoryFactExtractionRepository()
    extraction = make_extraction()
    repository.extractions[extraction.id] = extraction
    repository.force_conflict = True
    review = CandidateFactReviewService(repository, clock=lambda: NOW)

    with pytest.raises(CandidateFactReviewConflictError):
        await review.review(
            extraction.id,
            extraction.proposals[0].id,
            ProposalReviewStatus.ACCEPTED,
        )
