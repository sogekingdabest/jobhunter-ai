"""Fictional job offer fixtures with exact offsets."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from jobhunter.ai.contracts.job_offers import JobOfferNormalizationOutput
from jobhunter.jobs.domain.offers import (
    JobFieldName,
    JobOffer,
    JobOfferField,
    JobRequirement,
    JobSource,
    RequirementPriority,
    RequirementType,
)

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
JOB_TEXT = "Acme Labs\nBackend Engineer\nMadrid · Hybrid\nMust have Python and SQL."


def evidence(quote: str) -> dict[str, object]:
    start = JOB_TEXT.index(quote)
    return {"quote": quote, "start_offset": start, "end_offset": start + len(quote)}


def normalization_payload() -> dict[str, object]:
    return {
        "contract_version": "1.0",
        "company": {"value": "Acme Labs", "evidence": evidence("Acme Labs"), "confidence": 1},
        "title": {
            "value": "Backend Engineer",
            "evidence": evidence("Backend Engineer"),
            "confidence": 1,
        },
        "location": {"value": "Madrid", "evidence": evidence("Madrid"), "confidence": 0.99},
        "remote_type": {
            "value": "hybrid",
            "evidence": evidence("Hybrid"),
            "confidence": 0.95,
        },
        "employment_type": None,
        "seniority": None,
        "requirements": [
            {
                "requirement_type": "skill",
                "priority": "required",
                "normalized_value": "Python",
                "evidence": evidence("Python"),
                "confidence": 1,
            },
            {
                "requirement_type": "skill",
                "priority": "required",
                "normalized_value": "SQL",
                "evidence": evidence("SQL"),
                "confidence": 1,
            },
        ],
        "warnings": [],
    }


def make_normalization() -> JobOfferNormalizationOutput:
    return JobOfferNormalizationOutput.model_validate(normalization_payload())


def make_offer(*, offer_id: UUID | None = None, source_id: UUID | None = None) -> JobOffer:
    offer_id = offer_id or uuid4()
    source_id = source_id or uuid4()
    field = JobOfferField(
        id=uuid4(),
        job_offer_id=offer_id,
        evidence_span_id=uuid4(),
        name=JobFieldName.TITLE,
        value="Backend Engineer",
        evidence_quote="Backend Engineer",
        start_offset=10,
        end_offset=26,
        confidence=1,
    )
    requirement = JobRequirement(
        id=uuid4(),
        job_offer_id=offer_id,
        evidence_span_id=uuid4(),
        requirement_type=RequirementType.SKILL,
        priority=RequirementPriority.REQUIRED,
        normalized_value="Python",
        original_text="Python",
        start_offset=48,
        end_offset=54,
        confidence=1,
    )
    return JobOffer(
        id=offer_id,
        evidence_source_id=source_id,
        source=JobSource.MANUAL,
        raw_text=JOB_TEXT,
        content_fingerprint="a" * 64,
        normalization_version="1.0",
        fields=(field,),
        requirements=(requirement,),
        warnings=(),
        discovered_at=NOW,
    )
