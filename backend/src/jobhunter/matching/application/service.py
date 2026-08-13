"""Orchestrate matching without coupling policy to persistence."""

from datetime import datetime
from uuid import UUID, uuid4

from jobhunter.ai.domain.embeddings import EmbeddingRequest, EmbeddingTask
from jobhunter.ai.ports.embeddings import EmbeddingProvider
from jobhunter.candidate.ports.repository import CandidateProfileRepository
from jobhunter.jobs.ports.repository import JobOfferRepository
from jobhunter.matching.application.errors import (
    MatchAssessmentNotFoundError,
    MatchCandidateNotFoundError,
    MatchJobOfferNotFoundError,
)
from jobhunter.matching.domain.assessments import MatchAssessment
from jobhunter.matching.domain.hybrid import combine_semantic_analysis
from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from jobhunter.matching.domain.semantic import (
    SemanticDocument,
    SemanticEmbedding,
    analyze_semantics,
    candidate_documents,
    job_documents,
)
from jobhunter.matching.ports.embeddings import SemanticEmbeddingRepository
from jobhunter.matching.ports.repository import MatchAssessmentRepository


class MatchingService:
    """Load trusted aggregates, apply structured/semantic policies, and persist a snapshot."""

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        candidate_repository: CandidateProfileRepository,
        job_repository: JobOfferRepository,
        assessment_repository: MatchAssessmentRepository,
        policy: StructuredMatchingPolicy | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        embedding_repository: SemanticEmbeddingRepository | None = None,
    ) -> None:
        self._candidates = candidate_repository
        self._jobs = job_repository
        self._assessments = assessment_repository
        self._policy = policy or StructuredMatchingPolicy()
        if (embedding_provider is None) != (embedding_repository is None):
            raise ValueError("incomplete_semantic_matching_dependencies")
        self._embedding_provider = embedding_provider
        self._embedding_repository = embedding_repository

    async def assess(
        self,
        candidate_profile_id: UUID,
        job_offer_id: UUID,
        *,
        assessed_at: datetime | None = None,
    ) -> MatchAssessment:
        candidate = await self._candidates.get(candidate_profile_id)
        if candidate is None:
            raise MatchCandidateNotFoundError
        offer = await self._jobs.get(job_offer_id)
        if offer is None:
            raise MatchJobOfferNotFoundError
        assessment = self._policy.assess(candidate, offer, assessed_at=assessed_at)
        if self._embedding_provider is not None and self._embedding_repository is not None:
            candidate_embeddings = await self._embed(
                candidate_documents(candidate), EmbeddingTask.DOCUMENT
            )
            job_embeddings = await self._embed(job_documents(offer), EmbeddingTask.QUERY)
            assessment = combine_semantic_analysis(
                assessment,
                analyze_semantics(candidate_embeddings, job_embeddings),
                self._embedding_provider.model,
            )
        return await self._assessments.add(assessment)

    async def get(self, assessment_id: UUID) -> MatchAssessment:
        assessment = await self._assessments.get(assessment_id)
        if assessment is None:
            raise MatchAssessmentNotFoundError
        return assessment

    async def _embed(
        self,
        documents: tuple[SemanticDocument, ...],
        task: EmbeddingTask,
    ) -> tuple[SemanticEmbedding, ...]:
        provider = self._embedding_provider
        repository = self._embedding_repository
        if provider is None or repository is None:  # pragma: no cover - constructor invariant
            raise RuntimeError("semantic_matching_not_configured")
        found: dict[SemanticDocument, SemanticEmbedding] = {}
        missing: list[SemanticDocument] = []
        for document in documents:
            cached = await repository.get(document, provider.model)
            if cached is None:
                missing.append(document)
            else:
                found[document] = cached
        if missing:
            vectors = await provider.embed(
                tuple(EmbeddingRequest(document.text, task) for document in missing)
            )
            if len(vectors) != len(missing):
                raise ValueError("embedding_provider_result_count_mismatch")
            created = tuple(
                SemanticEmbedding(uuid4(), document, provider.model, vector)
                for document, vector in zip(missing, vectors, strict=True)
            )
            stored = await repository.add_many(created)
            if len(stored) != len(created):
                raise ValueError("embedding_repository_result_count_mismatch")
            found.update((item.document, item) for item in stored)
        return tuple(found[document] for document in documents)
