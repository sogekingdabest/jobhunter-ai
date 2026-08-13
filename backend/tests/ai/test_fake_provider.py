"""Tests for deterministic offline AI adapters."""

from datetime import UTC, datetime

import pytest

from jobhunter.ai.domain.errors import ProviderUnavailableError
from jobhunter.ai.domain.observability import AIInvocationEvent, InvocationOutcome
from jobhunter.ai.domain.types import TokenUsage
from jobhunter.ai.infrastructure.fake import (
    FakeStructuredFixture,
    FakeStructuredLLMProvider,
    InMemoryAIObservabilitySink,
)
from tests.ai.factories import make_provider_info, make_request, valid_output


def test_fake_fixture_requires_exactly_one_outcome() -> None:
    with pytest.raises(ValueError, match="fake_fixture_requires_one_outcome"):
        FakeStructuredFixture()
    with pytest.raises(ValueError, match="fake_fixture_requires_one_outcome"):
        FakeStructuredFixture(output=valid_output(), error=ProviderUnavailableError())


@pytest.mark.asyncio
async def test_fake_provider_returns_a_deep_copy_and_records_request() -> None:
    request = make_request()
    original = valid_output()
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {request.id: FakeStructuredFixture(output=original, usage=TokenUsage(5, 2))},
    )

    response = await provider.generate_structured(request)
    response.output["warnings"] = ["mutated by consumer"]

    assert provider.info.model == "fake-structured-v1"
    assert provider.requests == [request]
    assert original == valid_output()
    assert response.usage == TokenUsage(5, 2)


@pytest.mark.asyncio
async def test_fake_provider_raises_configured_or_missing_error() -> None:
    configured = make_request()
    missing = make_request()
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {configured.id: FakeStructuredFixture(error=ProviderUnavailableError())},
    )

    with pytest.raises(ProviderUnavailableError):
        await provider.generate_structured(configured)
    with pytest.raises(ProviderUnavailableError):
        await provider.generate_structured(missing)


def test_in_memory_sink_collects_events_without_copying_content() -> None:
    sink = InMemoryAIObservabilitySink()
    request = make_request()
    event = AIInvocationEvent(
        occurred_at=datetime(2026, 8, 13, tzinfo=UTC),
        request_id=request.id,
        task=request.task,
        provider="fake",
        model="fake-structured-v1",
        execution_location=make_provider_info().execution_location,
        outcome=InvocationOutcome.SUCCESS,
        duration_ms=12.0,
        input_count=1,
        usage=TokenUsage(5, 2),
    )

    assert sink.events == []
    sink.record(event)
    assert sink.events == [event]
