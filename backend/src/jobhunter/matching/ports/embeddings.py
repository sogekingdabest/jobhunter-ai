"""Persistence boundary for versioned semantic embedding caches."""

from typing import Protocol

from jobhunter.ai.domain.embeddings import EmbeddingModel
from jobhunter.matching.domain.semantic import SemanticDocument, SemanticEmbedding


class SemanticEmbeddingRepository(Protocol):  # pragma: no cover - structural contract
    async def get(
        self, document: SemanticDocument, model: EmbeddingModel
    ) -> SemanticEmbedding | None: ...

    async def add_many(
        self, embeddings: tuple[SemanticEmbedding, ...]
    ) -> tuple[SemanticEmbedding, ...]: ...
