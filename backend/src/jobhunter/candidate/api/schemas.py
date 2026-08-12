"""Validated API contracts for manual candidate profile editing."""

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from jobhunter.candidate.domain.competencies import (
    Competency,
    CompetencyCategory,
    LanguageLevel,
    LanguageProficiency,
)
from jobhunter.candidate.domain.experience import Education, Project, WorkExperience
from jobhunter.candidate.domain.profile import CandidateProfile, RemotePreference

ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class CandidateSchema(BaseModel):
    """Shared strict and whitespace-normalizing API behavior."""

    model_config = ConfigDict(extra="forbid", from_attributes=True, str_strip_whitespace=True)


class WorkExperienceInput(CandidateSchema):
    id: UUID | None = None
    employer: ShortText
    title: ShortText
    start_date: date | None = None
    end_date: date | None = None
    description: Annotated[str, Field(min_length=1, max_length=5000)] | None = None


class EducationInput(CandidateSchema):
    id: UUID | None = None
    institution: ShortText
    qualification: ShortText
    field_of_study: ShortText | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectInput(CandidateSchema):
    id: UUID | None = None
    name: ShortText
    description: Annotated[str, Field(min_length=1, max_length=5000)] | None = None
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None


class CompetencyInput(CandidateSchema):
    id: UUID | None = None
    name: Annotated[str, Field(min_length=1, max_length=150)]
    category: CompetencyCategory
    months_experience: Annotated[int, Field(ge=0, le=1200)] | None = None


class LanguageInput(CandidateSchema):
    id: UUID | None = None
    language: Annotated[str, Field(min_length=1, max_length=100)]
    level: LanguageLevel


class CandidateProfileInput(CandidateSchema):
    """Full aggregate replacement contract used by POST and PUT."""

    full_name: ShortText
    headline: Annotated[str, Field(min_length=1, max_length=250)] | None = None
    summary: Annotated[str, Field(min_length=1, max_length=10000)] | None = None
    email: Annotated[str, Field(min_length=3, max_length=320)] | None = None
    phone: Annotated[str, Field(min_length=3, max_length=50)] | None = None
    location: ShortText | None = None
    remote_preference: RemotePreference | None = None
    preferred_roles: list[ShortText] = Field(default_factory=list, max_length=30)
    preferred_locations: list[ShortText] = Field(default_factory=list, max_length=30)
    work_experiences: list[WorkExperienceInput] = Field(default_factory=list, max_length=100)
    education: list[EducationInput] = Field(default_factory=list, max_length=100)
    projects: list[ProjectInput] = Field(default_factory=list, max_length=100)
    competencies: list[CompetencyInput] = Field(default_factory=list, max_length=300)
    languages: list[LanguageInput] = Field(default_factory=list, max_length=50)

    def to_domain(
        self,
        *,
        profile_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> CandidateProfile:
        """Create a domain aggregate and provenance source for this user statement."""

        now = datetime.now(UTC)
        source_id = uuid4()
        return CandidateProfile(
            id=profile_id or uuid4(),
            evidence_source_id=source_id,
            full_name=self.full_name,
            headline=self.headline,
            summary=self.summary,
            email=self.email,
            phone=self.phone,
            location=self.location,
            remote_preference=self.remote_preference,
            preferred_roles=tuple(self.preferred_roles),
            preferred_locations=tuple(self.preferred_locations),
            work_experiences=tuple(
                WorkExperience(
                    id=item.id or uuid4(),
                    evidence_source_id=source_id,
                    **item.model_dump(exclude={"id"}),
                )
                for item in self.work_experiences
            ),
            education=tuple(
                Education(
                    id=item.id or uuid4(),
                    evidence_source_id=source_id,
                    **item.model_dump(exclude={"id"}),
                )
                for item in self.education
            ),
            projects=tuple(
                Project(
                    id=item.id or uuid4(),
                    evidence_source_id=source_id,
                    **item.model_dump(exclude={"id"}),
                )
                for item in self.projects
            ),
            competencies=tuple(
                Competency(
                    id=item.id or uuid4(),
                    evidence_source_id=source_id,
                    **item.model_dump(exclude={"id"}),
                )
                for item in self.competencies
            ),
            languages=tuple(
                LanguageProficiency(
                    id=item.id or uuid4(),
                    evidence_source_id=source_id,
                    **item.model_dump(exclude={"id"}),
                )
                for item in self.languages
            ),
            created_at=created_at or now,
            updated_at=now,
        )


class EvidenceResponse(CandidateSchema):
    id: UUID
    evidence_source_id: UUID


class WorkExperienceResponse(WorkExperienceInput, EvidenceResponse):
    id: UUID


class EducationResponse(EducationInput, EvidenceResponse):
    id: UUID


class ProjectResponse(ProjectInput, EvidenceResponse):
    id: UUID


class CompetencyResponse(CompetencyInput, EvidenceResponse):
    id: UUID


class LanguageResponse(LanguageInput, EvidenceResponse):
    id: UUID


class CandidateProfileResponse(CandidateSchema):
    """Complete profile returned to clients, including provenance identities."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evidence_source_id: UUID
    full_name: str
    headline: str | None
    summary: str | None
    email: str | None
    phone: str | None
    location: str | None
    remote_preference: RemotePreference | None
    preferred_roles: tuple[str, ...]
    preferred_locations: tuple[str, ...]
    work_experiences: tuple[WorkExperienceResponse, ...]
    education: tuple[EducationResponse, ...]
    projects: tuple[ProjectResponse, ...]
    competencies: tuple[CompetencyResponse, ...]
    languages: tuple[LanguageResponse, ...]
    created_at: datetime
    updated_at: datetime
