"""Regression harness used before accepting an embedding model revision."""

import json
from pathlib import Path

import pytest

from jobhunter.ai.infrastructure.fake_embeddings import FakeEmbeddingProvider
from jobhunter.matching.evaluation.ranking import RankingCase, RankingEvaluation, evaluate_ranking


def load_cases() -> tuple[RankingCase, ...]:
    path = Path(__file__).parents[1] / "fixtures" / "matching" / "semantic_ranking.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(RankingCase(**item) for item in payload["cases"])


@pytest.mark.asyncio
async def test_semantic_ranking_regression_fixture() -> None:
    cases = load_cases()
    vectors = {
        "Diseñar APIs backend robustas con Python": (1, 0, 0),
        "Built reliable Python APIs and backend services": (1, 0, 0),
        "Created visual identity and marketing campaigns": (0, 1, 0),
        "Operate cloud infrastructure and deployment pipelines": (0, 0, 1),
        "Administré infraestructura cloud y pipelines CI/CD": (0, 0, 1),
        "Managed retail sales and customer support": (0, 1, 0),
    }

    result = await evaluate_ranking(FakeEmbeddingProvider(vectors), cases)

    assert result == RankingEvaluation(total=2, first_choice_correct=2)
    assert result.accuracy_at_one == 1
    assert RankingEvaluation(0, 0).accuracy_at_one == 0


def test_ranking_case_validates_inputs() -> None:
    with pytest.raises(ValueError, match="invalid_semantic_ranking_case"):
        RankingCase("", ("candidate",), 0)
    with pytest.raises(ValueError, match="invalid_semantic_ranking_expected_index"):
        RankingCase("query", ("candidate",), 1)
