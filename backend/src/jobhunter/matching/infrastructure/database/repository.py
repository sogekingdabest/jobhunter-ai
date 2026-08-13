"""SQLAlchemy repository for immutable match assessments."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.matching.domain.assessments import (
    MatchAssessment,
    MatchDimension,
    MatchEvidence,
    RequirementGate,
)
from jobhunter.matching.domain.semantic import SemanticMatchEvidence
from jobhunter.matching.infrastructure.database.models import (
    MatchAssessmentModel,
    MatchDimensionModel,
    MatchEvidenceModel,
    RequirementGateModel,
    SemanticMatchEvidenceModel,
)


class SqlAlchemyMatchAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, assessment: MatchAssessment) -> MatchAssessment:
        self._session.add(_to_model(assessment))
        await self._session.commit()
        return await self._required(assessment.id)

    async def get(self, assessment_id: UUID) -> MatchAssessment | None:
        model = await self._session.scalar(
            self._statement().where(MatchAssessmentModel.id == assessment_id)
        )
        if model is None:
            return None
        return _to_domain(model)

    @staticmethod
    def _statement() -> Select[tuple[MatchAssessmentModel]]:
        return select(MatchAssessmentModel).options(
            selectinload(MatchAssessmentModel.dimensions).selectinload(
                MatchDimensionModel.evidence
            ),
            selectinload(MatchAssessmentModel.gates),
            selectinload(MatchAssessmentModel.semantic_evidence),
        )

    async def _required(self, assessment_id: UUID) -> MatchAssessment:
        stored = await self.get(assessment_id)
        if stored is None:  # pragma: no cover - protected by the completed transaction
            raise RuntimeError("match_assessment_not_persisted")
        return stored


def _to_model(assessment: MatchAssessment) -> MatchAssessmentModel:
    return MatchAssessmentModel(
        id=assessment.id,
        candidate_profile_id=assessment.candidate_profile_id,
        job_offer_id=assessment.job_offer_id,
        policy_version=assessment.policy_version,
        taxonomy_version=assessment.taxonomy_version,
        candidate_updated_at=assessment.candidate_updated_at,
        job_content_fingerprint=assessment.job_content_fingerprint,
        job_normalization_version=assessment.job_normalization_version,
        score=assessment.score,
        structured_score=assessment.structured_score,
        semantic_score=assessment.semantic_score,
        semantic_weight=assessment.semantic_weight,
        embedding_provider=assessment.embedding_provider,
        embedding_model=assessment.embedding_model,
        embedding_revision=assessment.embedding_revision,
        embedding_dimensions=assessment.embedding_dimensions,
        recommendation=assessment.recommendation,
        assessed_at=assessment.assessed_at,
        dimensions=[
            MatchDimensionModel(
                id=dimension.id,
                assessment_id=assessment.id,
                position=dimension_position,
                name=dimension.name,
                score=dimension.score,
                weight=dimension.weight,
                evidence=[
                    MatchEvidenceModel(
                        id=evidence.id,
                        dimension_id=dimension.id,
                        position=evidence_position,
                        outcome=evidence.outcome,
                        score=evidence.score,
                        explanation_code=evidence.explanation_code,
                        job_value=evidence.job_value,
                        candidate_fact_ids=[str(value) for value in evidence.candidate_fact_ids],
                        candidate_values=list(evidence.candidate_values),
                        job_requirement_id=evidence.job_requirement_id,
                        job_field_id=evidence.job_field_id,
                    )
                    for evidence_position, evidence in enumerate(dimension.evidence)
                ],
            )
            for dimension_position, dimension in enumerate(assessment.dimensions)
        ],
        gates=[
            RequirementGateModel(
                id=gate.id,
                assessment_id=assessment.id,
                position=position,
                job_requirement_id=gate.job_requirement_id,
                status=gate.status,
                explanation_code=gate.explanation_code,
            )
            for position, gate in enumerate(assessment.gates)
        ],
        semantic_evidence=[
            SemanticMatchEvidenceModel(
                id=evidence.id,
                assessment_id=assessment.id,
                position=position,
                job_source_type=evidence.job_source_type,
                job_source_id=evidence.job_source_id,
                candidate_source_type=evidence.candidate_source_type,
                candidate_source_id=evidence.candidate_source_id,
                similarity=evidence.similarity,
            )
            for position, evidence in enumerate(assessment.semantic_evidence)
        ],
    )


def _to_domain(model: MatchAssessmentModel) -> MatchAssessment:
    return MatchAssessment(
        id=model.id,
        candidate_profile_id=model.candidate_profile_id,
        job_offer_id=model.job_offer_id,
        policy_version=model.policy_version,
        taxonomy_version=model.taxonomy_version,
        candidate_updated_at=model.candidate_updated_at,
        job_content_fingerprint=model.job_content_fingerprint,
        job_normalization_version=model.job_normalization_version,
        score=model.score,
        structured_score=model.structured_score,
        semantic_score=model.semantic_score,
        semantic_weight=model.semantic_weight,
        embedding_provider=model.embedding_provider,
        embedding_model=model.embedding_model,
        embedding_revision=model.embedding_revision,
        embedding_dimensions=model.embedding_dimensions,
        semantic_evidence=tuple(
            SemanticMatchEvidence(
                evidence.id,
                evidence.job_source_type,
                evidence.job_source_id,
                evidence.candidate_source_type,
                evidence.candidate_source_id,
                evidence.similarity,
            )
            for evidence in model.semantic_evidence
        ),
        recommendation=model.recommendation,
        dimensions=tuple(
            MatchDimension(
                id=dimension.id,
                name=dimension.name,
                score=dimension.score,
                weight=dimension.weight,
                evidence=tuple(
                    MatchEvidence(
                        id=evidence.id,
                        dimension=dimension.name,
                        outcome=evidence.outcome,
                        score=evidence.score,
                        explanation_code=evidence.explanation_code,
                        job_value=evidence.job_value,
                        candidate_fact_ids=tuple(
                            UUID(value) for value in evidence.candidate_fact_ids
                        ),
                        candidate_values=tuple(evidence.candidate_values),
                        job_requirement_id=evidence.job_requirement_id,
                        job_field_id=evidence.job_field_id,
                    )
                    for evidence in dimension.evidence
                ),
            )
            for dimension in model.dimensions
        ),
        gates=tuple(
            RequirementGate(
                id=gate.id,
                job_requirement_id=gate.job_requirement_id,
                status=gate.status,
                explanation_code=gate.explanation_code,
            )
            for gate in model.gates
        ),
        assessed_at=model.assessed_at,
    )
