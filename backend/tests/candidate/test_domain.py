"""Unit tests for candidate aggregate invariants."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from jobhunter.candidate.domain.competencies import (
    Competency,
    CompetencyCategory,
    LanguageLevel,
    LanguageProficiency,
)
from jobhunter.candidate.domain.experience import Education, Project, WorkExperience
from jobhunter.candidate.domain.profile import CandidateProfile
from tests.candidate.factories import make_profile

EXPECTED_MONTHS_EXPERIENCE = 36
EXPECTED_NESTED_ENTITIES = 5


def test_complete_candidate_profile_is_valid() -> None:
    profile = make_profile()

    assert profile.full_name == "Ada Lovelace"
    assert profile.competencies[0].months_experience == EXPECTED_MONTHS_EXPERIENCE
    assert len(profile.entity_ids) == EXPECTED_NESTED_ENTITIES


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (
            lambda: WorkExperience(uuid4(), uuid4(), " ", "Engineer"),
            "missing_employer",
        ),
        (
            lambda: WorkExperience(uuid4(), uuid4(), "Company", " "),
            "missing_title",
        ),
        (
            lambda: WorkExperience(
                uuid4(), uuid4(), "Company", "Engineer", date(2025, 1, 1), date(2024, 1, 1)
            ),
            "invalid_date_range",
        ),
        (
            lambda: Education(uuid4(), uuid4(), " ", "BSc"),
            "missing_institution",
        ),
        (
            lambda: Education(uuid4(), uuid4(), "University", " "),
            "missing_qualification",
        ),
        (
            lambda: Education(
                uuid4(), uuid4(), "University", "BSc", None, date(2025, 1, 1), date(2024, 1, 1)
            ),
            "invalid_date_range",
        ),
        (lambda: Project(uuid4(), uuid4(), " "), "missing_project_name"),
        (
            lambda: Competency(uuid4(), uuid4(), " ", CompetencyCategory.OTHER),
            "missing_competency_name",
        ),
        (
            lambda: Competency(uuid4(), uuid4(), "Python", CompetencyCategory.OTHER, -1),
            "invalid_months_experience",
        ),
        (
            lambda: LanguageProficiency(uuid4(), uuid4(), " ", LanguageLevel.BASIC),
            "missing_language",
        ),
    ],
)
def test_nested_entities_reject_invalid_facts(factory: object, expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        factory()  # type: ignore[operator]


def test_profile_rejects_missing_name() -> None:
    with pytest.raises(ValueError, match="missing_full_name"):
        CandidateProfile(
            id=uuid4(),
            evidence_source_id=uuid4(),
            full_name=" ",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"preferred_roles": ("Backend", " backend ")}, "duplicate_preferred_role"),
        ({"preferred_locations": ("Madrid", " ")}, "missing_preferred_location"),
    ],
)
def test_profile_rejects_invalid_preferences(change: dict[str, object], expected: str) -> None:
    profile = make_profile()
    arguments = {field: getattr(profile, field) for field in profile.__dataclass_fields__}
    arguments.update(change)

    with pytest.raises(ValueError, match=expected):
        CandidateProfile(**arguments)


def test_profile_rejects_duplicate_nested_identity() -> None:
    profile = make_profile()
    duplicate = Project(
        id=profile.work_experiences[0].id,
        evidence_source_id=profile.evidence_source_id,
        name="Duplicate id",
    )
    arguments = {field: getattr(profile, field) for field in profile.__dataclass_fields__}
    arguments["projects"] = (duplicate,)

    with pytest.raises(ValueError, match="duplicate_entity_id"):
        CandidateProfile(**arguments)


def test_profile_rejects_duplicate_competency_and_language_names() -> None:
    profile = make_profile()
    arguments = {field: getattr(profile, field) for field in profile.__dataclass_fields__}
    arguments["competencies"] = (
        profile.competencies[0],
        Competency(
            uuid4(),
            profile.evidence_source_id,
            " python ",
            CompetencyCategory.PROGRAMMING_LANGUAGE,
        ),
    )
    with pytest.raises(ValueError, match="duplicate_competency"):
        CandidateProfile(**arguments)

    arguments["competencies"] = profile.competencies
    arguments["languages"] = (
        profile.languages[0],
        LanguageProficiency(uuid4(), profile.evidence_source_id, "english", LanguageLevel.NATIVE),
    )
    with pytest.raises(ValueError, match="duplicate_language"):
        CandidateProfile(**arguments)
