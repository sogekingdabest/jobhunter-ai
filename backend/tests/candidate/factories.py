"""Reusable candidate domain fixtures."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from jobhunter.candidate.domain.competencies import (
    Competency,
    CompetencyCategory,
    LanguageLevel,
    LanguageProficiency,
)
from jobhunter.candidate.domain.experience import Education, Project, WorkExperience
from jobhunter.candidate.domain.profile import CandidateProfile, RemotePreference


def make_profile(
    *, profile_id: UUID | None = None, source_id: UUID | None = None
) -> CandidateProfile:
    evidence_source_id = source_id or uuid4()
    now = datetime.now(UTC)
    return CandidateProfile(
        id=profile_id or uuid4(),
        evidence_source_id=evidence_source_id,
        full_name="Ada Lovelace",
        headline="Backend Engineer",
        summary="Builds reliable services.",
        email="ada@example.test",
        phone="+34 600 000 000",
        location="Madrid",
        remote_preference=RemotePreference.HYBRID,
        preferred_roles=("Backend Engineer",),
        preferred_locations=("Madrid", "Remote EU"),
        work_experiences=(
            WorkExperience(
                id=uuid4(),
                evidence_source_id=evidence_source_id,
                employer="Analytical Engines",
                title="Software Engineer",
                start_date=date(2023, 1, 1),
                description="Designed APIs.",
            ),
        ),
        education=(
            Education(
                id=uuid4(),
                evidence_source_id=evidence_source_id,
                institution="University of London",
                qualification="BSc",
                field_of_study="Mathematics",
            ),
        ),
        projects=(
            Project(
                id=uuid4(),
                evidence_source_id=evidence_source_id,
                name="JobHunter AI",
                description="Explainable job matching.",
                url="https://example.test/project",
            ),
        ),
        competencies=(
            Competency(
                id=uuid4(),
                evidence_source_id=evidence_source_id,
                name="Python",
                category=CompetencyCategory.PROGRAMMING_LANGUAGE,
                months_experience=36,
            ),
        ),
        languages=(
            LanguageProficiency(
                id=uuid4(),
                evidence_source_id=evidence_source_id,
                language="English",
                level=LanguageLevel.FLUENT,
            ),
        ),
        created_at=now,
        updated_at=now,
    )
