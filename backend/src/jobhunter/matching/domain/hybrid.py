"""Versioned combination of structured and semantic matching signals."""

from dataclasses import replace

from jobhunter.ai.domain.embeddings import EmbeddingModel
from jobhunter.matching.domain.assessments import (
    GOOD_MATCH_THRESHOLD,
    STRONG_MATCH_THRESHOLD,
    GateStatus,
    MatchAssessment,
    MatchRecommendation,
)
from jobhunter.matching.domain.semantic import SemanticAnalysis

HYBRID_POLICY_VERSION = "hybrid-v1"
SEMANTIC_WEIGHT = 0.25


def combine_semantic_analysis(
    structured: MatchAssessment,
    analysis: SemanticAnalysis,
    model: EmbeddingModel,
) -> MatchAssessment:
    """Add a bounded semantic signal without changing mandatory gates."""

    if analysis.score is None:
        return structured
    score = round(
        structured.structured_score * (1 - SEMANTIC_WEIGHT) + analysis.score * SEMANTIC_WEIGHT,
        2,
    )
    return replace(
        structured,
        policy_version=HYBRID_POLICY_VERSION,
        score=score,
        semantic_score=analysis.score,
        semantic_weight=SEMANTIC_WEIGHT,
        embedding_provider=model.provider,
        embedding_model=model.model,
        embedding_revision=model.revision,
        embedding_dimensions=model.dimensions,
        semantic_evidence=analysis.evidence,
        recommendation=_recommendation(score, structured),
    )


def _recommendation(score: float, assessment: MatchAssessment) -> MatchRecommendation:
    if any(item.status is GateStatus.FAILED for item in assessment.gates):
        return MatchRecommendation.BLOCKED
    if any(item.status is GateStatus.NEEDS_REVIEW for item in assessment.gates):
        return MatchRecommendation.NEEDS_REVIEW
    if score >= STRONG_MATCH_THRESHOLD:
        return MatchRecommendation.STRONG_MATCH
    if score >= GOOD_MATCH_THRESHOLD:
        return MatchRecommendation.GOOD_MATCH
    return MatchRecommendation.WEAK_MATCH
