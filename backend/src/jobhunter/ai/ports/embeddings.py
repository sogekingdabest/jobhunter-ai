"""Port implemented by local, browser-mediated, or cloud embedding adapters."""

from typing import Protocol

from jobhunter.ai.domain.embeddings import EmbeddingModel, EmbeddingRequest, EmbeddingVector


class EmbeddingProvider(Protocol):  # pragma: no cover - structural typing contract
    @property
    def model(self) -> EmbeddingModel:
        """Return versioned model metadata without loading the model."""

    async def embed(self, requests: tuple[EmbeddingRequest, ...]) -> tuple[EmbeddingVector, ...]:
        """Return one vector per request, preserving input order."""
