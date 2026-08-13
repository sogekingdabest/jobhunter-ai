"""Invariant tests for persisted matching snapshots."""

from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest

from jobhunter.matching.domain.assessments import (
    GateStatus,
    MatchAssessment,
    MatchDimensionName,
    MatchOutcome,
    MatchRecommendation,
)
from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer


def valid_assessment() -> MatchAssessment:
    return StructuredMatchingPolicy().assess(make_profile(), make_offer())


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"score": 101}, "invalid_match_evidence_score"),
        ({"explanation_code": " "}, "missing_match_explanation_code"),
        ({"job_value": " "}, "missing_match_job_value"),
        ({"candidate_values": ("",)}, "empty_match_candidate_value"),
        (
            {"outcome": MatchOutcome.UNKNOWN, "score": 1},
            "unknown_match_evidence_has_score",
        ),
        (
            {"outcome": MatchOutcome.MATCHED, "score": None},
            "scored_match_evidence_missing_score",
        ),
        ({"job_requirement_id": None}, "match_evidence_missing_job_fact"),
        ({"job_field_id": uuid4()}, "match_evidence_has_multiple_job_facts"),
        ({"candidate_fact_ids": (uuid4(),) * 2}, "duplicate_candidate_match_fact"),
    ],
)
def test_match_evidence_rejects_inconsistent_state(changes: dict[str, Any], error: str) -> None:
    assessment = valid_assessment()
    evidence = assessment.dimensions[0].evidence[0]

    with pytest.raises(ValueError, match=error):
        replace(evidence, **changes)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("score", "invalid_match_dimension_score"),
        ("weight", "invalid_match_dimension_weight"),
        ("empty", "empty_match_dimension_evidence"),
        ("foreign", "foreign_match_dimension_evidence"),
        ("duplicate", "duplicate_match_evidence_id"),
        ("inconsistent", "inconsistent_match_dimension_score"),
    ],
)
def test_match_dimension_rejects_inconsistent_state(mutation: str, error: str) -> None:
    assessment = valid_assessment()
    dimension = assessment.dimensions[0]
    evidence = dimension.evidence[0]
    changes: dict[str, Any]
    if mutation == "score":
        changes = {"score": -1}
    elif mutation == "weight":
        changes = {"weight": 0}
    elif mutation == "empty":
        changes = {"evidence": ()}
    elif mutation == "foreign":
        changes = {"evidence": (replace(evidence, dimension=MatchDimensionName.LOCATION),)}
    elif mutation == "duplicate":
        changes = {"evidence": (evidence, evidence)}
    else:
        changes = {"score": None}

    with pytest.raises(ValueError, match=error):
        replace(dimension, **changes)


def test_requirement_gate_requires_an_explanation() -> None:
    gate = valid_assessment().gates[0]

    with pytest.raises(ValueError, match="missing_gate_explanation_code"):
        replace(gate, explanation_code="")


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("version", "missing_match_version"),
        ("fingerprint", "invalid_match_job_fingerprint"),
        ("score", "invalid_match_score"),
        ("dimension_name", "duplicate_match_dimension"),
        ("dimension_id", "duplicate_match_dimension_id"),
        ("gate", "duplicate_requirement_gate"),
        ("recommendation", "inconsistent_match_recommendation"),
    ],
)
def test_match_assessment_rejects_inconsistent_state(mutation: str, error: str) -> None:
    profile = make_profile()
    offer = make_offer()
    assessment = StructuredMatchingPolicy().assess(profile, offer)
    location_offer = replace(
        offer,
        fields=(
            replace(
                offer.fields[0],
                name=offer.fields[0].name.LOCATION,
                value="Madrid",
                evidence_quote="Madrid",
            ),
        ),
        requirements=(),
    )
    location_assessment = StructuredMatchingPolicy().assess(profile, location_offer)
    changes: dict[str, Any]
    if mutation == "version":
        changes = {"policy_version": ""}
    elif mutation == "fingerprint":
        changes = {"job_content_fingerprint": "bad"}
    elif mutation == "score":
        changes = {"score": -1}
    elif mutation == "dimension_name":
        changes = {"dimensions": (assessment.dimensions[0], assessment.dimensions[0])}
    elif mutation == "dimension_id":
        second = replace(location_assessment.dimensions[0], id=assessment.dimensions[0].id)
        changes = {"dimensions": (assessment.dimensions[0], second)}
    elif mutation == "gate":
        changes = {"gates": (assessment.gates[0], assessment.gates[0])}
    else:
        changes = {"recommendation": MatchRecommendation.GOOD_MATCH}

    with pytest.raises(ValueError, match=error):
        replace(assessment, **changes)


def test_gate_status_still_controls_recommendation_invariant() -> None:
    assessment = valid_assessment()
    gate = replace(assessment.gates[0], status=GateStatus.NEEDS_REVIEW)

    with pytest.raises(ValueError, match="inconsistent_match_recommendation"):
        replace(assessment, gates=(gate,))
