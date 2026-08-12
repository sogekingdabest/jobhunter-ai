"""Candidate profile aggregate root."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from jobhunter.candidate.domain.common import ensure_unique_ids, ensure_unique_text, require_text
from jobhunter.candidate.domain.competencies import Competency, LanguageProficiency
from jobhunter.candidate.domain.experience import Education, Project, WorkExperience


class RemotePreference(StrEnum):
    """Candidate preference for workplace location."""

    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    FLEXIBLE = "flexible"


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    """Master professional profile and sole source of candidate truth."""

    id: UUID
    evidence_source_id: UUID
    full_name: str
    created_at: datetime
    updated_at: datetime
    headline: str | None = None
    summary: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    remote_preference: RemotePreference | None = None
    preferred_roles: tuple[str, ...] = ()
    preferred_locations: tuple[str, ...] = ()
    work_experiences: tuple[WorkExperience, ...] = ()
    education: tuple[Education, ...] = ()
    projects: tuple[Project, ...] = ()
    competencies: tuple[Competency, ...] = ()
    languages: tuple[LanguageProficiency, ...] = ()

    def __post_init__(self) -> None:
        require_text(self.full_name, "full_name")
        ensure_unique_text(self.preferred_roles, "preferred_role")
        ensure_unique_text(self.preferred_locations, "preferred_location")
        nested_ids = (
            *(item.id for item in self.work_experiences),
            *(item.id for item in self.education),
            *(item.id for item in self.projects),
            *(item.id for item in self.competencies),
            *(item.id for item in self.languages),
        )
        ensure_unique_ids(nested_ids)
        ensure_unique_text(
            (f"{item.category.value}:{item.name.strip()}" for item in self.competencies),
            "competency",
        )
        ensure_unique_text((item.language for item in self.languages), "language")
