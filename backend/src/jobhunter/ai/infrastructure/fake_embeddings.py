"""Deterministic embedding adapter for tests and evaluation fixtures."""

from collections.abc import Mapping

from jobhunter.ai.domain.embeddings import (
    EmbeddingModel,
    EmbeddingRequest,
    EmbeddingVector,
)


class FakeEmbeddingProvider:
    """Return scripted vectors while exercising the real provider contract."""

    def __init__(
        self,
        vectors: Mapping[str, tuple[float, ...]],
        *,
        model: EmbeddingModel | None = None,
    ) -> None:
        dimensions = len(next(iter(vectors.values()))) if vectors else 3
        self._model = model or EmbeddingModel("fake", "scripted", "v1", dimensions)
        self._vectors = dict(vectors)
        self.requests: list[tuple[EmbeddingRequest, ...]] = []

    @property
    def model(self) -> EmbeddingModel:
        return self._model

    async def embed(self, requests: tuple[EmbeddingRequest, ...]) -> tuple[EmbeddingVector, ...]:
        self.requests.append(requests)
        vectors = tuple(EmbeddingVector(self._vectors[item.text]) for item in requests)
        if any(len(item.values) != self._model.dimensions for item in vectors):
            raise ValueError("embedding_provider_dimension_mismatch")
        return vectors
