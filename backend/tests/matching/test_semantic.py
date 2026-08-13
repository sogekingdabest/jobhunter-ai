"""Semantic projection, similarity, and hybrid policy tests."""

from dataclasses import replace
from uuid import uuid4

import pytest

from jobhunter.ai.domain.embeddings import EmbeddingModel, EmbeddingVector
from jobhunter.jobs.domain.offers import RequirementPriority, RequirementType
from jobhunter.matching.domain.hybrid import HYBRID_POLICY_VERSION, combine_semantic_analysis
from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from jobhunter.matching.domain.semantic import (
    SemanticAnalysis,
    SemanticDocument,
    SemanticEmbedding,
    SemanticMatchEvidence,
    SemanticSourceType,
    analyze_semantics,
    candidate_documents,
    cosine_similarity,
    job_documents,
)
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer
from tests.matching.factories import offer_with, requirement

MODEL = EmbeddingModel("google", "embeddinggemma-300m", "2025-09", 2)
SHA256_LENGTH = 64
PERFECT_SCORE = 100


def document(source_type: SemanticSourceType, *, candidate: bool) -> SemanticDocument:
    return SemanticDocument(
        source_type,
        uuid4(),
        "professional text",
        candidate_profile_id=uuid4() if candidate else None,
        job_offer_id=None if candidate else uuid4(),
    )


def test_semantic_documents_exclude_contact_data_and_keep_provenance() -> None:
    profile = make_profile()
    offer = offer_with(
        requirements=(
            requirement(
                "Design reliable APIs",
                RequirementType.RESPONSIBILITY,
                RequirementPriority.UNSPECIFIED,
            ),
        )
    )

    candidate = candidate_documents(profile)
    job = job_documents(offer)
    assert profile.email is not None
    assert profile.phone is not None

    assert {item.source_type for item in candidate} == {
        SemanticSourceType.CANDIDATE_SUMMARY,
        SemanticSourceType.CANDIDATE_WORK_EXPERIENCE,
        SemanticSourceType.CANDIDATE_PROJECT,
    }
    assert all(
        profile.email not in item.text and profile.phone not in item.text for item in candidate
    )
    assert job[0].source_type is SemanticSourceType.JOB_DESCRIPTION
    assert job[1].source_id == offer.requirements[0].id
    assert len(candidate[0].content_hash) == SHA256_LENGTH
    no_overview = replace(profile, headline=None, summary=None)
    assert all(
        item.source_type is not SemanticSourceType.CANDIDATE_SUMMARY
        for item in candidate_documents(no_overview)
    )


def test_semantic_value_invariants_reject_invalid_states() -> None:
    with pytest.raises(ValueError, match="missing_semantic_document_text"):
        replace(document(SemanticSourceType.CANDIDATE_SUMMARY, candidate=True), text="")
    with pytest.raises(ValueError, match="invalid_semantic_document_scope"):
        replace(
            document(SemanticSourceType.CANDIDATE_SUMMARY, candidate=True),
            job_offer_id=uuid4(),
        )
    with pytest.raises(ValueError, match="embedding_dimension_mismatch"):
        SemanticEmbedding(
            uuid4(),
            document(SemanticSourceType.CANDIDATE_SUMMARY, candidate=True),
            MODEL,
            EmbeddingVector((1,)),
        )
    evidence = SemanticMatchEvidence(
        uuid4(),
        SemanticSourceType.JOB_DESCRIPTION,
        uuid4(),
        SemanticSourceType.CANDIDATE_SUMMARY,
        uuid4(),
        0.5,
    )
    with pytest.raises(ValueError, match="invalid_semantic_similarity"):
        replace(evidence, similarity=2)
    with pytest.raises(ValueError, match="invalid_semantic_score"):
        SemanticAnalysis(101, (evidence,))
    with pytest.raises(ValueError, match="inconsistent_semantic_analysis"):
        SemanticAnalysis(None, (evidence,))


def test_cosine_similarity_is_bounded_and_requires_matching_dimensions() -> None:
    assert cosine_similarity(EmbeddingVector((1, 0)), EmbeddingVector((1, 0))) == 1
    assert cosine_similarity(EmbeddingVector((1, 0)), EmbeddingVector((-1, 0))) == 0
    with pytest.raises(ValueError, match="embedding_dimension_mismatch"):
        cosine_similarity(EmbeddingVector((1,)), EmbeddingVector((1, 0)))


def test_analysis_selects_best_candidate_source_for_each_job_text() -> None:
    candidate_one = SemanticEmbedding(
        uuid4(),
        document(SemanticSourceType.CANDIDATE_SUMMARY, candidate=True),
        MODEL,
        EmbeddingVector((1, 0)),
    )
    candidate_two = SemanticEmbedding(
        uuid4(),
        document(SemanticSourceType.CANDIDATE_PROJECT, candidate=True),
        MODEL,
        EmbeddingVector((0, 1)),
    )
    job = SemanticEmbedding(
        uuid4(),
        document(SemanticSourceType.JOB_DESCRIPTION, candidate=False),
        MODEL,
        EmbeddingVector((0, 1)),
    )

    result = analyze_semantics((candidate_one, candidate_two), (job,))

    assert result.score == PERFECT_SCORE
    assert result.evidence[0].candidate_source_id == candidate_two.document.source_id
    assert analyze_semantics((), (job,)) == SemanticAnalysis(None, ())


def test_hybrid_policy_combines_scores_but_preserves_mandatory_gates() -> None:
    structured = StructuredMatchingPolicy().assess(make_profile(), make_offer())
    evidence = SemanticMatchEvidence(
        uuid4(),
        SemanticSourceType.JOB_DESCRIPTION,
        uuid4(),
        SemanticSourceType.CANDIDATE_SUMMARY,
        uuid4(),
        1,
    )

    hybrid = combine_semantic_analysis(structured, SemanticAnalysis(100, (evidence,)), MODEL)

    assert hybrid.policy_version == HYBRID_POLICY_VERSION
    assert hybrid.score == round(structured.score * 0.75 + 25, 2)
    assert hybrid.gates == structured.gates
    assert hybrid.embedding_model == "embeddinggemma-300m"
    assert combine_semantic_analysis(structured, SemanticAnalysis(None, ()), MODEL) is structured


def test_hybrid_recommendations_cover_gates_and_score_bands() -> None:
    profile = make_profile()
    evidence = SemanticMatchEvidence(
        uuid4(),
        SemanticSourceType.JOB_DESCRIPTION,
        uuid4(),
        SemanticSourceType.CANDIDATE_SUMMARY,
        uuid4(),
        0,
    )
    analysis = SemanticAnalysis(0, (evidence,))
    blocked = StructuredMatchingPolicy().assess(replace(profile, competencies=()), make_offer())
    review_offer = offer_with(
        requirements=(requirement("Ambiguous mandatory duty", RequirementType.OTHER),)
    )
    review = StructuredMatchingPolicy().assess(profile, review_offer)
    preferred_match = StructuredMatchingPolicy().assess(
        profile,
        offer_with(
            requirements=(
                requirement("Python", RequirementType.SKILL, RequirementPriority.PREFERRED),
            )
        ),
    )
    preferred_missing = StructuredMatchingPolicy().assess(
        profile,
        offer_with(
            requirements=(
                requirement("Rust", RequirementType.SKILL, RequirementPriority.PREFERRED),
            )
        ),
    )

    assert combine_semantic_analysis(blocked, analysis, MODEL).recommendation.value == "blocked"
    assert combine_semantic_analysis(review, analysis, MODEL).recommendation.value == "needs_review"
    assert (
        combine_semantic_analysis(preferred_match, analysis, MODEL).recommendation.value
        == "good_match"
    )
    assert (
        combine_semantic_analysis(preferred_missing, analysis, MODEL).recommendation.value
        == "weak_match"
    )
