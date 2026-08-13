"""Domain invariants for normalized job offers."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest

from jobhunter.jobs.domain.offers import (
    EmploymentType,
    JobFieldName,
    JobSource,
    RemoteType,
    Seniority,
)
from tests.jobs.factories import make_offer


def test_offer_exposes_normalized_properties() -> None:
    offer = make_offer()
    base = offer.fields[0]
    extra = tuple(
        replace(base, id=uuid4(), evidence_span_id=uuid4(), name=name, value=value)
        for name, value in (
            (JobFieldName.COMPANY, "Acme Labs"),
            (JobFieldName.LOCATION, "Madrid"),
            (JobFieldName.REMOTE_TYPE, "hybrid"),
            (JobFieldName.EMPLOYMENT_TYPE, "full_time"),
            (JobFieldName.SENIORITY, "senior"),
        )
    )
    offer = replace(offer, fields=(base, *extra))

    assert offer.title == "Backend Engineer"
    assert offer.company == "Acme Labs"
    assert offer.location == "Madrid"
    assert offer.remote_type is RemoteType.HYBRID
    assert offer.employment_type is EmploymentType.FULL_TIME
    assert offer.seniority is Seniority.SENIOR
    assert offer.field_value(JobFieldName.COMPANY) == "Acme Labs"


def test_missing_optional_properties_are_none() -> None:
    offer = make_offer()
    assert offer.company is None
    assert offer.location is None
    assert offer.remote_type is None
    assert offer.employment_type is None
    assert offer.seniority is None


@pytest.mark.parametrize(
    ("target", "changes", "error"),
    [
        ("field", {"value": " "}, "missing_job_field_value"),
        ("field", {"evidence_quote": ""}, "missing_job_evidence"),
        ("field", {"start_offset": -1}, "invalid_job_evidence_offsets"),
        ("field", {"confidence": 2}, "invalid_job_field_confidence"),
        ("requirement", {"normalized_value": ""}, "missing_job_requirement_value"),
        ("requirement", {"end_offset": 0}, "invalid_job_evidence_offsets"),
        ("requirement", {"confidence": -0.1}, "invalid_job_requirement_confidence"),
    ],
)
def test_child_invariants(target: str, changes: dict[str, object], error: str) -> None:
    offer = make_offer()
    child = offer.fields[0] if target == "field" else offer.requirements[0]
    with pytest.raises(ValueError, match=error):
        replace(child, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"raw_text": " "}, "missing_job_offer_text"),
        ({"normalization_version": ""}, "missing_job_normalization_version"),
        ({"content_fingerprint": "bad"}, "invalid_job_content_fingerprint"),
        ({"content_fingerprint": "g" * 64}, "invalid_job_content_fingerprint"),
        ({"warnings": ("",)}, "empty_job_normalization_warning"),
    ],
)
def test_offer_scalar_invariants(changes: dict[str, object], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        replace(make_offer(), **changes)  # type: ignore[arg-type]


def test_offer_enforces_acquisition_url_invariants() -> None:
    offer = make_offer()
    with pytest.raises(ValueError, match="manual_job_offer_has_url"):
        replace(offer, source_url="https://jobs.example.com")
    with pytest.raises(ValueError, match="url_job_offer_missing_url"):
        replace(offer, source=JobSource.URL)
    with pytest.raises(ValueError, match="url_job_offer_missing_url"):
        replace(
            offer,
            source=JobSource.URL,
            source_url="https://jobs.example.com",
            canonical_url=" ",
        )


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        (lambda offer: {"fields": (offer.fields[0], offer.fields[0])}, "duplicate_job_field_id"),
        (
            lambda offer: {
                "fields": (
                    offer.fields[0],
                    replace(offer.fields[0], id=uuid4(), evidence_span_id=uuid4()),
                )
            },
            "duplicate_job_field_name",
        ),
        (
            lambda offer: {"requirements": (offer.requirements[0], offer.requirements[0])},
            "duplicate_job_requirement_id",
        ),
        (
            lambda offer: {"fields": (replace(offer.fields[0], job_offer_id=uuid4()),)},
            "foreign_job_offer_child",
        ),
        (
            lambda offer: {"requirements": (replace(offer.requirements[0], job_offer_id=uuid4()),)},
            "foreign_job_offer_child",
        ),
    ],
)
def test_offer_child_invariants(changes: Callable[[Any], dict[str, object]], error: str) -> None:
    offer = make_offer()
    mutation = changes(offer)
    with pytest.raises(ValueError, match=error):
        replace(offer, **mutation)  # type: ignore[arg-type]
