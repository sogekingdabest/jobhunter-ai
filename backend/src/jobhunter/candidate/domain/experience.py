"""Experience and portfolio entities owned by a candidate profile."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from jobhunter.candidate.domain.common import require_text


def _validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date is not None and end_date is not None and end_date < start_date:
        raise ValueError("invalid_date_range")


@dataclass(frozen=True, slots=True)
class WorkExperience:
    """One employment fact explicitly supported by candidate evidence."""

    id: UUID
    evidence_source_id: UUID
    employer: str
    title: str
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        require_text(self.employer, "employer")
        require_text(self.title, "title")
        _validate_date_range(self.start_date, self.end_date)


@dataclass(frozen=True, slots=True)
class Education:
    """One formal education fact."""

    id: UUID
    evidence_source_id: UUID
    institution: str
    qualification: str
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    def __post_init__(self) -> None:
        require_text(self.institution, "institution")
        require_text(self.qualification, "qualification")
        _validate_date_range(self.start_date, self.end_date)


@dataclass(frozen=True, slots=True)
class Project:
    """One candidate project that may be selected for a tailored CV."""

    id: UUID
    evidence_source_id: UUID
    name: str
    description: str | None = None
    url: str | None = None

    def __post_init__(self) -> None:
        require_text(self.name, "project_name")
