"""Candidate competency and language entities."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from jobhunter.candidate.domain.common import require_text


class CompetencyCategory(StrEnum):
    """High-level grouping used by matching and CV presentation."""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    DEVOPS = "devops"
    TOOL = "tool"
    SOFT_SKILL = "soft_skill"
    OTHER = "other"


class LanguageLevel(StrEnum):
    """Human-language proficiency without pretending false precision."""

    BASIC = "basic"
    CONVERSATIONAL = "conversational"
    PROFESSIONAL = "professional"
    FLUENT = "fluent"
    NATIVE = "native"


@dataclass(frozen=True, slots=True)
class Competency:
    """One explicitly declared candidate competency."""

    id: UUID
    evidence_source_id: UUID
    name: str
    category: CompetencyCategory
    months_experience: int | None = None

    def __post_init__(self) -> None:
        require_text(self.name, "competency_name")
        if self.months_experience is not None and self.months_experience < 0:
            raise ValueError("invalid_months_experience")


@dataclass(frozen=True, slots=True)
class LanguageProficiency:
    """One human language and the level explicitly claimed by the user."""

    id: UUID
    evidence_source_id: UUID
    language: str
    level: LanguageLevel

    def __post_init__(self) -> None:
        require_text(self.language, "language")
