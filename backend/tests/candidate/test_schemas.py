"""Unit tests for candidate API contracts and domain conversion."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from jobhunter.candidate.api.schemas import CandidateProfileInput, CandidateProfileResponse


def sample_payload() -> dict[str, object]:
    return {
        "full_name": "  Ada Lovelace  ",
        "preferred_roles": ["Backend Engineer"],
        "work_experiences": [
            {
                "employer": "Analytical Engines",
                "title": "Software Engineer",
                "start_date": "2023-01-01",
            }
        ],
        "education": [{"institution": "University", "qualification": "BSc"}],
        "projects": [{"name": "JobHunter AI"}],
        "competencies": [
            {"name": "Python", "category": "programming_language", "months_experience": 36}
        ],
        "languages": [{"language": "English", "level": "fluent"}],
    }


def test_input_builds_traceable_domain_profile() -> None:
    payload = CandidateProfileInput.model_validate(sample_payload())
    profile = payload.to_domain()

    assert profile.full_name == "Ada Lovelace"
    assert all(
        item.evidence_source_id == profile.evidence_source_id
        for collection in (
            profile.work_experiences,
            profile.education,
            profile.projects,
            profile.competencies,
            profile.languages,
        )
        for item in collection
    )
    response = CandidateProfileResponse.model_validate(profile)
    assert response.competencies[0].name == "Python"


def test_input_preserves_explicit_id_and_creation_time_on_replace() -> None:
    item_id = uuid4()
    profile_id = uuid4()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    data = sample_payload()
    data["projects"] = [{"id": str(item_id), "name": "JobHunter AI"}]

    profile = CandidateProfileInput.model_validate(data).to_domain(
        profile_id=profile_id, created_at=created_at
    )

    assert profile.id == profile_id
    assert profile.projects[0].id == item_id
    assert profile.created_at == created_at


def test_input_forbids_unknown_fields() -> None:
    data = sample_payload()
    data["invented_skill"] = "Teleportation"

    with pytest.raises(ValidationError) as captured:
        CandidateProfileInput.model_validate(data)

    assert captured.value.errors()[0]["type"] == "extra_forbidden"
