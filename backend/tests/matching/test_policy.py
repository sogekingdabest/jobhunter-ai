"""Behavioral tests for structured matching policy v1."""

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from jobhunter.candidate.domain.competencies import Competency, LanguageLevel
from jobhunter.candidate.domain.experience import WorkExperience
from jobhunter.candidate.domain.profile import RemotePreference
from jobhunter.jobs.domain.offers import (
    JobFieldName,
    RequirementPriority,
    RequirementType,
)
from jobhunter.matching.domain.assessments import (
    GateStatus,
    MatchAssessment,
    MatchDimension,
    MatchDimensionName,
    MatchOutcome,
    MatchRecommendation,
)
from jobhunter.matching.domain.policy import POLICY_VERSION, StructuredMatchingPolicy
from tests.candidate.factories import make_profile
from tests.matching.factories import field, offer_with, requirement

ASSESSED_AT = datetime(2026, 8, 13, 12, tzinfo=UTC)


FULL_SCORE = 100
HALF_SCORE = 50


def by_dimension(assessment: MatchAssessment, name: MatchDimensionName) -> MatchDimension:
    return next(item for item in assessment.dimensions if item.name is name)


def test_policy_scores_explicit_facts_across_all_dimensions() -> None:
    candidate = replace(make_profile(), headline="Senior Backend Engineer")
    offer = offer_with(
        requirements=(
            requirement("Py", RequirementType.SKILL),
            requirement("3 years Python", RequirementType.EXPERIENCE),
            requirement("Bachelor degree", RequirementType.EDUCATION),
            requirement("English professional", RequirementType.LANGUAGE),
            requirement("Madrid", RequirementType.LOCATION),
        ),
        fields=(
            field(JobFieldName.SENIORITY, "senior"),
            field(JobFieldName.LOCATION, "Madrid"),
            field(JobFieldName.REMOTE_TYPE, "hybrid"),
        ),
    )

    assessment = StructuredMatchingPolicy().assess(candidate, offer, assessed_at=ASSESSED_AT)

    assert assessment.policy_version == POLICY_VERSION
    assert assessment.taxonomy_version == "skills-v1"
    assert assessment.score == FULL_SCORE
    assert assessment.recommendation is MatchRecommendation.STRONG_MATCH
    assert {item.status for item in assessment.gates} == {GateStatus.PASSED}
    assert {item.name for item in assessment.dimensions} == set(MatchDimensionName)
    skills = by_dimension(assessment, MatchDimensionName.SKILLS)
    assert skills.evidence[0].candidate_fact_ids == (candidate.competencies[0].id,)


def test_missing_mandatory_skill_blocks_without_hiding_score() -> None:
    offer = offer_with(
        requirements=(
            requirement("Kubernetes", RequirementType.SKILL),
            requirement("Python", RequirementType.SKILL, RequirementPriority.PREFERRED),
        )
    )

    assessment = StructuredMatchingPolicy().assess(make_profile(), offer, assessed_at=ASSESSED_AT)

    assert assessment.score == HALF_SCORE
    assert assessment.recommendation is MatchRecommendation.BLOCKED
    assert assessment.gates[0].status is GateStatus.FAILED


@pytest.mark.parametrize(
    ("requirement_type", "value", "expected_code"),
    [
        (RequirementType.EXPERIENCE, "Relevant experience", "experience_duration_unknown"),
        (RequirementType.EDUCATION, "Relevant studies", "education_level_unknown"),
        (RequirementType.LANGUAGE, "Another language", "language_name_unknown"),
    ],
)
def test_ambiguous_mandatory_requirement_needs_review(
    requirement_type: RequirementType, value: str, expected_code: str
) -> None:
    offer = offer_with(requirements=(requirement(value, requirement_type),))

    assessment = StructuredMatchingPolicy().assess(make_profile(), offer, assessed_at=ASSESSED_AT)

    assert assessment.score == 0
    assert assessment.recommendation is MatchRecommendation.NEEDS_REVIEW
    assert assessment.gates[0].status is GateStatus.NEEDS_REVIEW
    assert assessment.dimensions[0].evidence[0].explanation_code == expected_code


def test_unhandled_mandatory_requirement_needs_review_without_dimension() -> None:
    offer = offer_with(
        requirements=(requirement("Own the roadmap", RequirementType.RESPONSIBILITY),)
    )

    assessment = StructuredMatchingPolicy().assess(make_profile(), offer, assessed_at=ASSESSED_AT)

    assert assessment.recommendation is MatchRecommendation.NEEDS_REVIEW
    assert assessment.gates[0].explanation_code == "mandatory_requirement_not_deterministic"


def test_partial_experience_language_education_seniority_and_remote_are_explained() -> None:
    profile = make_profile()
    profile = replace(
        profile,
        headline="Junior Backend Engineer",
        education=(replace(profile.education[0], qualification="FP"),),
        languages=(replace(profile.languages[0], level=LanguageLevel.CONVERSATIONAL),),
        remote_preference=RemotePreference.ONSITE,
    )
    offer = offer_with(
        requirements=(
            requirement("6 years Python", RequirementType.EXPERIENCE),
            requirement("Bachelor", RequirementType.EDUCATION, RequirementPriority.PREFERRED),
            requirement("English fluent", RequirementType.LANGUAGE, RequirementPriority.PREFERRED),
        ),
        fields=(
            field(JobFieldName.SENIORITY, "senior"),
            field(JobFieldName.REMOTE_TYPE, "hybrid"),
        ),
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    assert assessment.recommendation is MatchRecommendation.BLOCKED
    assert all(item.evidence[0].outcome is MatchOutcome.PARTIAL for item in assessment.dimensions)
    assert by_dimension(assessment, MatchDimensionName.LOCATION).score == HALF_SCORE


def test_general_work_duration_deduplicates_overlapping_months() -> None:
    profile = make_profile()
    second = WorkExperience(
        id=profile.projects[0].id,
        evidence_source_id=profile.evidence_source_id,
        employer="Overlap Ltd",
        title="Engineer",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1),
    )
    profile = replace(
        profile,
        projects=(),
        work_experiences=(
            replace(profile.work_experiences[0], end_date=date(2025, 1, 1)),
            second,
        ),
    )
    offer = offer_with(
        requirements=(requirement("24 months professional experience", RequirementType.EXPERIENCE),)
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    evidence = assessment.dimensions[0].evidence[0]
    assert evidence.outcome is MatchOutcome.MATCHED
    assert len(evidence.candidate_fact_ids) == len(profile.work_experiences)


def test_unknown_candidate_durations_and_levels_are_not_assumed_missing() -> None:
    profile = make_profile()
    profile = replace(
        profile,
        work_experiences=(replace(profile.work_experiences[0], start_date=None),),
        competencies=(replace(profile.competencies[0], months_experience=None),),
        education=(replace(profile.education[0], qualification="Specialist certificate"),),
    )
    offer = offer_with(
        requirements=(
            requirement("3 years Python", RequirementType.EXPERIENCE),
            requirement("2 years professional experience", RequirementType.EXPERIENCE),
            requirement("Bachelor", RequirementType.EDUCATION),
        )
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    codes = {
        evidence.explanation_code
        for dimension in assessment.dimensions
        for evidence in dimension.evidence
    }
    assert codes == {
        "candidate_skill_duration_unknown",
        "candidate_experience_duration_unknown",
        "candidate_education_level_unknown",
    }
    assert assessment.recommendation is MatchRecommendation.NEEDS_REVIEW


def test_absent_facts_are_missing_and_unknown_preferences_are_unscored() -> None:
    profile = replace(
        make_profile(),
        work_experiences=(),
        education=(),
        languages=(),
        location=None,
        preferred_locations=(),
        remote_preference=None,
    )
    offer = offer_with(
        requirements=(
            requirement("1 year professional experience", RequirementType.EXPERIENCE),
            requirement("Bachelor", RequirementType.EDUCATION),
            requirement("English", RequirementType.LANGUAGE),
            requirement("Barcelona", RequirementType.LOCATION),
        ),
        fields=(
            field(JobFieldName.LOCATION, "Barcelona"),
            field(JobFieldName.REMOTE_TYPE, "remote"),
        ),
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    outcomes = [item.outcome for dimension in assessment.dimensions for item in dimension.evidence]
    assert outcomes.count(MatchOutcome.MISSING) == len(outcomes) - 1
    assert outcomes.count(MatchOutcome.UNKNOWN) == 1


def test_unscored_seniority_and_non_required_unknowns_yield_weak_match() -> None:
    profile = replace(make_profile(), headline="Backend Engineer", work_experiences=())
    offer = offer_with(
        requirements=(
            requirement("Experience", RequirementType.EXPERIENCE, RequirementPriority.PREFERRED),
        ),
        fields=(field(JobFieldName.SENIORITY, "senior"),),
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    assert assessment.score == 0
    assert assessment.recommendation is MatchRecommendation.WEAK_MATCH
    assert all(item.score is None for item in assessment.dimensions)


def test_good_match_threshold_is_reported_without_gates() -> None:
    offer = offer_with(
        requirements=(
            requirement("Python", RequirementType.SKILL, RequirementPriority.PREFERRED),
            requirement("Kubernetes", RequirementType.SKILL, RequirementPriority.PREFERRED),
            requirement("Docker", RequirementType.SKILL, RequirementPriority.PREFERRED),
        )
    )
    profile = make_profile()
    profile = replace(
        profile,
        competencies=(
            *profile.competencies,
            Competency(
                id=profile.projects[0].id,
                evidence_source_id=profile.evidence_source_id,
                name="Docker",
                category=profile.competencies[0].category,
            ),
        ),
        projects=(),
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    assert assessment.score == pytest.approx(66.67)
    assert assessment.recommendation is MatchRecommendation.GOOD_MATCH


def test_location_and_remote_mismatches_are_scored() -> None:
    profile = replace(make_profile(), remote_preference=RemotePreference.REMOTE)
    offer = offer_with(
        fields=(
            field(JobFieldName.LOCATION, "Barcelona"),
            field(JobFieldName.REMOTE_TYPE, "onsite"),
        )
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    dimension = assessment.dimensions[0]
    assert dimension.score == 0
    assert {item.explanation_code for item in dimension.evidence} == {
        "offer_location_not_preferred",
        "remote_preference_mismatch",
    }


def test_missing_skill_experience_and_language_without_level_are_deterministic() -> None:
    profile = replace(make_profile(), competencies=(), languages=make_profile().languages)
    offer = offer_with(
        requirements=(
            requirement("3 years Python", RequirementType.EXPERIENCE),
            requirement("English", RequirementType.LANGUAGE, RequirementPriority.PREFERRED),
        )
    )

    assessment = StructuredMatchingPolicy().assess(profile, offer, assessed_at=ASSESSED_AT)

    evidence = [item for dimension in assessment.dimensions for item in dimension.evidence]
    assert evidence[0].outcome is MatchOutcome.MISSING
    assert evidence[1].explanation_code == "language_declared"


def test_duration_with_unknown_scope_requires_review_instead_of_using_total_experience() -> None:
    offer = offer_with(
        requirements=(requirement("3 years distributed systems", RequirementType.EXPERIENCE),)
    )

    assessment = StructuredMatchingPolicy().assess(make_profile(), offer, assessed_at=ASSESSED_AT)

    assert assessment.dimensions[0].evidence[0].explanation_code == "experience_scope_unknown"
    assert assessment.recommendation is MatchRecommendation.NEEDS_REVIEW
