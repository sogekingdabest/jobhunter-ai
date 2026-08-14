"""Traceable tailored resume aggregate."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

JOB_FINGERPRINT_LENGTH = 64


class ResumeStatus(StrEnum):
    """Human-review lifecycle for a generated resume."""

    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ResumeSection(StrEnum):
    HEADER = "header"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    SKILLS = "skills"
    LANGUAGES = "languages"


class ResumeSourceType(StrEnum):
    PROFILE = "profile"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    PROJECT = "project"
    COMPETENCY = "competency"
    LANGUAGE = "language"


class GenerationMethod(StrEnum):
    EXTRACTIVE = "extractive"
    LLM_REPHRASED = "llm_rephrased"


@dataclass(frozen=True, slots=True)
class ResumeSource:
    """Immutable snapshot of one master-profile fact used by a fragment."""

    id: UUID
    source_type: ResumeSourceType
    source_id: UUID
    evidence_source_id: UUID
    source_text: str

    def __post_init__(self) -> None:
        if not self.source_text.strip():
            raise ValueError("missing_resume_source_text")


@dataclass(frozen=True, slots=True)
class ResumeFragment:
    """Displayed text with explicit links to all supporting facts."""

    id: UUID
    resume_id: UUID
    section: ResumeSection
    position: int
    generated_text: str
    method: GenerationMethod
    sources: tuple[ResumeSource, ...]

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("invalid_resume_fragment_position")
        if not self.generated_text.strip():
            raise ValueError("missing_resume_fragment_text")
        if not self.sources:
            raise ValueError("ungrounded_resume_fragment")
        if len({source.id for source in self.sources}) != len(self.sources):
            raise ValueError("duplicate_resume_source")


@dataclass(frozen=True, slots=True)
class TailoredResume:
    """Versioned CV draft that can only be approved by the user."""

    id: UUID
    candidate_profile_id: UUID
    job_offer_id: UUID
    match_assessment_id: UUID
    generation_version: str
    candidate_updated_at: datetime
    job_content_fingerprint: str
    status: ResumeStatus
    fragments: tuple[ResumeFragment, ...]
    created_at: datetime
    revision: int = 0
    reviewed_at: datetime | None = None
    provider: str | None = None
    model: str | None = None

    def __post_init__(self) -> None:
        if not self.generation_version.strip():
            raise ValueError("missing_resume_generation_version")
        if len(self.job_content_fingerprint) != JOB_FINGERPRINT_LENGTH:
            raise ValueError("invalid_resume_job_fingerprint")
        if self.revision < 0:
            raise ValueError("invalid_resume_revision")
        if not self.fragments:
            raise ValueError("empty_tailored_resume")
        if any(fragment.resume_id != self.id for fragment in self.fragments):
            raise ValueError("foreign_resume_fragment")
        positions = tuple(fragment.position for fragment in self.fragments)
        if positions != tuple(range(len(self.fragments))):
            raise ValueError("invalid_resume_fragment_order")
        has_llm = any(
            fragment.method is GenerationMethod.LLM_REPHRASED for fragment in self.fragments
        )
        if has_llm != (self.provider is not None and self.model is not None):
            raise ValueError("inconsistent_resume_provider_metadata")
        if (self.status is ResumeStatus.NEEDS_REVIEW) != (self.reviewed_at is None):
            raise ValueError("invalid_resume_review_state")

    def review(self, decision: ResumeStatus, *, reviewed_at: datetime) -> "TailoredResume":
        if self.status is not ResumeStatus.NEEDS_REVIEW:
            raise ValueError("resume_already_reviewed")
        if decision is ResumeStatus.NEEDS_REVIEW:
            raise ValueError("invalid_resume_review_decision")
        return replace(
            self,
            status=decision,
            reviewed_at=reviewed_at,
            revision=self.revision + 1,
        )
