"""Embedding contract and deterministic adapter tests."""

import math

import pytest

from jobhunter.ai.domain.embeddings import (
    EmbeddingModel,
    EmbeddingRequest,
    EmbeddingTask,
    EmbeddingVector,
)
from jobhunter.ai.infrastructure.fake_embeddings import FakeEmbeddingProvider


def test_embedding_values_validate_identity_text_dimensions_and_numbers() -> None:
    with pytest.raises(ValueError, match="missing_embedding_model_identity"):
        EmbeddingModel("", "model", "v1", 3)
    with pytest.raises(ValueError, match="invalid_embedding_dimensions"):
        EmbeddingModel("local", "model", "v1", 0)
    with pytest.raises(ValueError, match="missing_embedding_text"):
        EmbeddingRequest(" ", EmbeddingTask.QUERY)
    with pytest.raises(ValueError, match="empty_embedding_vector"):
        EmbeddingVector(())
    with pytest.raises(ValueError, match="non_finite_embedding_value"):
        EmbeddingVector((math.inf,))
    with pytest.raises(ValueError, match="zero_embedding_vector"):
        EmbeddingVector((0, 0))


@pytest.mark.asyncio
async def test_fake_embedding_provider_preserves_order_and_records_requests() -> None:
    requests = (
        EmbeddingRequest("query", EmbeddingTask.QUERY),
        EmbeddingRequest("document", EmbeddingTask.DOCUMENT),
    )
    provider = FakeEmbeddingProvider({"query": (1, 0), "document": (0, 1)})

    vectors = await provider.embed(requests)

    assert vectors == (EmbeddingVector((1, 0)), EmbeddingVector((0, 1)))
    assert provider.requests == [requests]


@pytest.mark.asyncio
async def test_fake_embedding_provider_rejects_wrong_dimensions() -> None:
    provider = FakeEmbeddingProvider({"valid": (1, 0), "bad": (1,)})

    with pytest.raises(ValueError, match="embedding_provider_dimension_mismatch"):
        await provider.embed((EmbeddingRequest("bad", EmbeddingTask.QUERY),))
