"""Factories for deterministic matching scenarios."""

from dataclasses import replace
from uuid import uuid4

from jobhunter.jobs.domain.offers import (
    JobFieldName,
    JobOffer,
    JobOfferField,
    JobRequirement,
    RequirementPriority,
    RequirementType,
)
from tests.jobs.factories import make_offer


def requirement(
    value: str,
    requirement_type: RequirementType,
    priority: RequirementPriority = RequirementPriority.REQUIRED,
) -> JobRequirement:
    offer_id = uuid4()
    return JobRequirement(
        id=uuid4(),
        job_offer_id=offer_id,
        evidence_span_id=uuid4(),
        requirement_type=requirement_type,
        priority=priority,
        normalized_value=value,
        original_text=value,
        start_offset=0,
        end_offset=len(value),
        confidence=1,
    )


def field(name: JobFieldName, value: str) -> JobOfferField:
    offer_id = uuid4()
    return JobOfferField(
        id=uuid4(),
        job_offer_id=offer_id,
        evidence_span_id=uuid4(),
        name=name,
        value=value,
        evidence_quote=value,
        start_offset=0,
        end_offset=len(value),
        confidence=1,
    )


def offer_with(
    *,
    requirements: tuple[JobRequirement, ...] = (),
    fields: tuple[JobOfferField, ...] = (),
) -> JobOffer:
    offer = make_offer()
    return replace(
        offer,
        requirements=tuple(replace(item, job_offer_id=offer.id) for item in requirements),
        fields=tuple(replace(item, job_offer_id=offer.id) for item in fields),
    )
