"""Small provider-neutral ranking regression harness."""

from dataclasses import dataclass

from jobhunter.ai.domain.embeddings import EmbeddingRequest, EmbeddingTask
from jobhunter.ai.ports.embeddings import EmbeddingProvider
from jobhunter.matching.domain.semantic import cosine_similarity


@dataclass(frozen=True, slots=True)
class RankingCase:
    query: str
    candidates: tuple[str, ...]
    expected_first: int

    def __post_init__(self) -> None:
        if not self.query.strip() or not self.candidates:
            raise ValueError("invalid_semantic_ranking_case")
        if not 0 <= self.expected_first < len(self.candidates):
            raise ValueError("invalid_semantic_ranking_expected_index")


@dataclass(frozen=True, slots=True)
class RankingEvaluation:
    total: int
    first_choice_correct: int

    @property
    def accuracy_at_one(self) -> float:
        return self.first_choice_correct / self.total if self.total else 0


async def evaluate_ranking(
    provider: EmbeddingProvider, cases: tuple[RankingCase, ...]
) -> RankingEvaluation:
    correct = 0
    for case in cases:
        query = (await provider.embed((EmbeddingRequest(case.query, EmbeddingTask.QUERY),)))[0]
        candidates = await provider.embed(
            tuple(EmbeddingRequest(text, EmbeddingTask.DOCUMENT) for text in case.candidates)
        )
        best = max(
            range(len(candidates)),
            key=lambda index: cosine_similarity(query, candidates[index]),
        )
        correct += best == case.expected_first
    return RankingEvaluation(len(cases), correct)
