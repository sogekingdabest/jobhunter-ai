"""Provider-neutral embedding values shared by semantic features."""

import math
from dataclasses import dataclass
from enum import StrEnum


class EmbeddingTask(StrEnum):
    """Distinguish asymmetric retrieval inputs without provider-specific prompts."""

    QUERY = "query"
    DOCUMENT = "document"


@dataclass(frozen=True, slots=True)
class EmbeddingModel:
    """Immutable identity of the model that produced a vector."""

    provider: str
    model: str
    revision: str
    dimensions: int

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip() or not self.revision.strip():
            raise ValueError("missing_embedding_model_identity")
        if not 1 <= self.dimensions <= MAX_EMBEDDING_DIMENSIONS:
            raise ValueError("invalid_embedding_dimensions")


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    text: str
    task: EmbeddingTask

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("missing_embedding_text")


@dataclass(frozen=True, slots=True)
class EmbeddingVector:
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("empty_embedding_vector")
        if any(not math.isfinite(value) for value in self.values):
            raise ValueError("non_finite_embedding_value")
        if not any(value != 0 for value in self.values):
            raise ValueError("zero_embedding_vector")


MAX_EMBEDDING_DIMENSIONS = 2000
