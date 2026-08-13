"""Deterministic preparation and scoring around interchangeable embeddings."""

import hashlib
import math
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from jobhunter.ai.domain.embeddings import EmbeddingModel, EmbeddingVector
from jobhunter.candidate.domain.profile import CandidateProfile
from jobhunter.jobs.domain.offers import JobOffer, RequirementType

MAX_SEMANTIC_TEXT_CHARACTERS = 6000
MAX_SEMANTIC_SCORE = 100


class SemanticSourceType(StrEnum):
    CANDIDATE_SUMMARY = "candidate_summary"
    CANDIDATE_WORK_EXPERIENCE = "candidate_work_experience"
    CANDIDATE_PROJECT = "candidate_project"
    JOB_DESCRIPTION = "job_description"
    JOB_RESPONSIBILITY = "job_responsibility"


@dataclass(frozen=True, slots=True)
class SemanticDocument:
    """Minimal text projection tied to one trusted domain source."""

    source_type: SemanticSourceType
    source_id: UUID
    text: str
    candidate_profile_id: UUID | None = None
    job_offer_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("missing_semantic_document_text")
        if (self.candidate_profile_id is None) == (self.job_offer_id is None):
            raise ValueError("invalid_semantic_document_scope")

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class SemanticEmbedding:
    id: UUID
    document: SemanticDocument
    model: EmbeddingModel
    vector: EmbeddingVector

    def __post_init__(self) -> None:
        if len(self.vector.values) != self.model.dimensions:
            raise ValueError("embedding_dimension_mismatch")


@dataclass(frozen=True, slots=True)
class SemanticMatchEvidence:
    """Best candidate source for one job-side semantic query."""

    id: UUID
    job_source_type: SemanticSourceType
    job_source_id: UUID
    candidate_source_type: SemanticSourceType
    candidate_source_id: UUID
    similarity: float

    def __post_init__(self) -> None:
        if not 0 <= self.similarity <= 1:
            raise ValueError("invalid_semantic_similarity")


@dataclass(frozen=True, slots=True)
class SemanticAnalysis:
    score: float | None
    evidence: tuple[SemanticMatchEvidence, ...]

    def __post_init__(self) -> None:
        if self.score is not None and not 0 <= self.score <= MAX_SEMANTIC_SCORE:
            raise ValueError("invalid_semantic_score")
        if (self.score is None) != (not self.evidence):
            raise ValueError("inconsistent_semantic_analysis")


def candidate_documents(candidate: CandidateProfile) -> tuple[SemanticDocument, ...]:
    """Project only non-contact professional facts for semantic comparison."""

    documents: list[SemanticDocument] = []
    overview = _join(candidate.headline, candidate.summary)
    if overview:
        documents.append(
            SemanticDocument(
                SemanticSourceType.CANDIDATE_SUMMARY,
                candidate.id,
                overview,
                candidate_profile_id=candidate.id,
            )
        )
    documents.extend(
        SemanticDocument(
            SemanticSourceType.CANDIDATE_WORK_EXPERIENCE,
            item.id,
            _join(item.title, item.employer, item.description),
            candidate_profile_id=candidate.id,
        )
        for item in candidate.work_experiences
    )
    documents.extend(
        SemanticDocument(
            SemanticSourceType.CANDIDATE_PROJECT,
            item.id,
            _join(item.name, item.description),
            candidate_profile_id=candidate.id,
        )
        for item in candidate.projects
    )
    return tuple(documents)


def job_documents(offer: JobOffer) -> tuple[SemanticDocument, ...]:
    """Treat untrusted offer content strictly as embedding data, never instructions."""

    documents = [
        SemanticDocument(
            SemanticSourceType.JOB_DESCRIPTION,
            offer.id,
            offer.raw_text[:MAX_SEMANTIC_TEXT_CHARACTERS],
            job_offer_id=offer.id,
        )
    ]
    documents.extend(
        SemanticDocument(
            SemanticSourceType.JOB_RESPONSIBILITY,
            requirement.id,
            requirement.normalized_value,
            job_offer_id=offer.id,
        )
        for requirement in offer.requirements
        if requirement.requirement_type is RequirementType.RESPONSIBILITY
    )
    return tuple(documents)


def analyze_semantics(
    candidate: tuple[SemanticEmbedding, ...],
    job: tuple[SemanticEmbedding, ...],
) -> SemanticAnalysis:
    if not candidate or not job:
        return SemanticAnalysis(None, ())
    evidence: list[SemanticMatchEvidence] = []
    for job_item in job:
        candidate_item, similarity = max(
            (
                (_candidate, cosine_similarity(_candidate.vector, job_item.vector))
                for _candidate in candidate
            ),
            key=lambda item: item[1],
        )
        evidence.append(
            SemanticMatchEvidence(
                uuid4(),
                job_item.document.source_type,
                job_item.document.source_id,
                candidate_item.document.source_type,
                candidate_item.document.source_id,
                round(similarity, 6),
            )
        )
    return SemanticAnalysis(
        round(sum(item.similarity for item in evidence) / len(evidence) * 100, 2),
        tuple(evidence),
    )


def cosine_similarity(left: EmbeddingVector, right: EmbeddingVector) -> float:
    if len(left.values) != len(right.values):
        raise ValueError("embedding_dimension_mismatch")
    dot = sum(a * b for a, b in zip(left.values, right.values, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left.values))
    right_norm = math.sqrt(sum(value * value for value in right.values))
    raw = dot / (left_norm * right_norm)
    return min(1.0, max(0.0, raw))


def _join(*values: str | None) -> str:
    return "\n".join(value.strip() for value in values if value and value.strip())
