"""Normalized job offer aggregate with exact source evidence."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

SHA256_LENGTH = 64


class JobSource(StrEnum):
    """Supported acquisition channels."""

    MANUAL = "manual"
    URL = "url"


class JobFieldName(StrEnum):
    """Normalized scalar fields extracted from an offer."""

    COMPANY = "company"
    TITLE = "title"
    LOCATION = "location"
    REMOTE_TYPE = "remote_type"
    EMPLOYMENT_TYPE = "employment_type"
    SENIORITY = "seniority"


class RemoteType(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


class Seniority(StrEnum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"


class RequirementType(StrEnum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    LANGUAGE = "language"
    LOCATION = "location"
    RESPONSIBILITY = "responsibility"
    OTHER = "other"


class RequirementPriority(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNSPECIFIED = "unspecified"


def _require_text(value: str, code: str) -> None:
    if not value.strip():
        raise ValueError(code)


def _validate_evidence(quote: str, start_offset: int, end_offset: int) -> None:
    _require_text(quote, "missing_job_evidence")
    if start_offset < 0 or end_offset <= start_offset:
        raise ValueError("invalid_job_evidence_offsets")


@dataclass(frozen=True, slots=True)
class JobOfferField:
    """One normalized scalar value grounded in exact offer text."""

    id: UUID
    job_offer_id: UUID
    evidence_span_id: UUID
    name: JobFieldName
    value: str
    evidence_quote: str
    start_offset: int
    end_offset: int
    confidence: float

    def __post_init__(self) -> None:
        _require_text(self.value, "missing_job_field_value")
        _validate_evidence(self.evidence_quote, self.start_offset, self.end_offset)
        if not 0 <= self.confidence <= 1:
            raise ValueError("invalid_job_field_confidence")


@dataclass(frozen=True, slots=True)
class JobRequirement:
    """One classified requirement grounded in exact offer text."""

    id: UUID
    job_offer_id: UUID
    evidence_span_id: UUID
    requirement_type: RequirementType
    priority: RequirementPriority
    normalized_value: str
    original_text: str
    start_offset: int
    end_offset: int
    confidence: float

    def __post_init__(self) -> None:
        _require_text(self.normalized_value, "missing_job_requirement_value")
        _validate_evidence(self.original_text, self.start_offset, self.end_offset)
        if not 0 <= self.confidence <= 1:
            raise ValueError("invalid_job_requirement_confidence")


@dataclass(frozen=True, slots=True)
class JobOffer:
    """Manual source text plus validated normalized facts."""

    id: UUID
    evidence_source_id: UUID
    source: JobSource
    source_url: str | None
    canonical_url: str | None
    raw_text: str
    content_fingerprint: str
    normalization_version: str
    fields: tuple[JobOfferField, ...]
    requirements: tuple[JobRequirement, ...]
    warnings: tuple[str, ...]
    discovered_at: datetime

    def __post_init__(self) -> None:
        _require_text(self.raw_text, "missing_job_offer_text")
        _require_text(self.normalization_version, "missing_job_normalization_version")
        if len(self.content_fingerprint) != SHA256_LENGTH or any(
            character not in "0123456789abcdef" for character in self.content_fingerprint
        ):
            raise ValueError("invalid_job_content_fingerprint")
        if any(not warning.strip() for warning in self.warnings):
            raise ValueError("empty_job_normalization_warning")
        if self.source is JobSource.MANUAL and (
            self.source_url is not None or self.canonical_url is not None
        ):
            raise ValueError("manual_job_offer_has_url")
        if self.source is JobSource.URL and (
            self.source_url is None
            or self.canonical_url is None
            or not self.source_url.strip()
            or not self.canonical_url.strip()
        ):
            raise ValueError("url_job_offer_missing_url")
        if len({field.id for field in self.fields}) != len(self.fields):
            raise ValueError("duplicate_job_field_id")
        if len({field.name for field in self.fields}) != len(self.fields):
            raise ValueError("duplicate_job_field_name")
        if len({item.id for item in self.requirements}) != len(self.requirements):
            raise ValueError("duplicate_job_requirement_id")
        if any(field.job_offer_id != self.id for field in self.fields) or any(
            item.job_offer_id != self.id for item in self.requirements
        ):
            raise ValueError("foreign_job_offer_child")

    def field_value(self, name: JobFieldName) -> str | None:
        """Return a normalized scalar value without exposing storage details."""

        return next((field.value for field in self.fields if field.name is name), None)

    @property
    def company(self) -> str | None:
        return self.field_value(JobFieldName.COMPANY)

    @property
    def title(self) -> str | None:
        return self.field_value(JobFieldName.TITLE)

    @property
    def location(self) -> str | None:
        return self.field_value(JobFieldName.LOCATION)

    @property
    def remote_type(self) -> RemoteType | None:
        value = self.field_value(JobFieldName.REMOTE_TYPE)
        return None if value is None else RemoteType(value)

    @property
    def employment_type(self) -> EmploymentType | None:
        value = self.field_value(JobFieldName.EMPLOYMENT_TYPE)
        return None if value is None else EmploymentType(value)

    @property
    def seniority(self) -> Seniority | None:
        value = self.field_value(JobFieldName.SENIORITY)
        return None if value is None else Seniority(value)
