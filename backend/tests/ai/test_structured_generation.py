"""Tests for privacy-gated structured generation orchestration."""

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobhunter.ai.application.structured_generation import StructuredGenerationService
from jobhunter.ai.domain.errors import (
    InvalidResponseSchemaError,
    InvalidStructuredOutputError,
    PrivacyPolicyViolationError,
    ProviderExecutionError,
    ProviderResponseMismatchError,
    ProviderUnavailableError,
)
from jobhunter.ai.domain.observability import InvocationOutcome
from jobhunter.ai.domain.privacy import AIPrivacyPolicy
from jobhunter.ai.domain.types import (
    ExecutionLocation,
    ProcessingConsent,
    ProviderInfo,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from jobhunter.ai.infrastructure.fake import (
    FakeStructuredFixture,
    FakeStructuredLLMProvider,
    InMemoryAIObservabilitySink,
)
from tests.ai.factories import make_provider_info, make_request, make_response, valid_output


class SequenceClock:
    def __init__(self, *values: float) -> None:
        self._values: Iterator[float] = iter(values)

    def __call__(self) -> float:
        return next(self._values)


class StubProvider:
    def __init__(
        self,
        info: ProviderInfo,
        *,
        response: StructuredGenerationResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.info = info
        self.response = response
        self.error = error

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        del request
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def make_service(
    provider: FakeStructuredLLMProvider | StubProvider,
    sink: InMemoryAIObservabilitySink,
) -> StructuredGenerationService:
    return StructuredGenerationService(
        provider,
        sink,
        privacy_policy=AIPrivacyPolicy(),
        monotonic_clock=SequenceClock(10.0, 10.025),
        wall_clock=lambda: datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_successful_generation_is_validated_and_observed_without_content() -> None:
    request = make_request()
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {request.id: FakeStructuredFixture(output=valid_output())},
    )
    sink = InMemoryAIObservabilitySink()

    response = await make_service(provider, sink).generate(request)

    assert response.output == valid_output()
    assert provider.requests == [request]
    event = sink.events[0]
    assert event.outcome is InvocationOutcome.SUCCESS
    assert event.duration_ms == pytest.approx(25.0)
    assert event.usage == response.usage
    assert "instruction" not in event.__dataclass_fields__
    assert "inputs" not in event.__dataclass_fields__
    assert "output" not in event.__dataclass_fields__


@pytest.mark.asyncio
async def test_cloud_processing_without_consent_is_blocked_before_provider_call() -> None:
    request = make_request()
    provider = FakeStructuredLLMProvider(
        make_provider_info(execution_location=ExecutionLocation.CLOUD),
        {request.id: FakeStructuredFixture(output=valid_output())},
    )
    sink = InMemoryAIObservabilitySink()

    with pytest.raises(PrivacyPolicyViolationError):
        await make_service(provider, sink).generate(request)

    assert provider.requests == []
    assert sink.events[0].outcome is InvocationOutcome.BLOCKED
    assert sink.events[0].error_code == "privacy_policy_violation"


@pytest.mark.asyncio
async def test_invalid_response_schema_is_rejected_before_provider_call() -> None:
    request = make_request(response_schema={"type": "not-a-json-schema-type"})
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {request.id: FakeStructuredFixture(output=valid_output())},
    )
    sink = InMemoryAIObservabilitySink()

    with pytest.raises(InvalidResponseSchemaError):
        await make_service(provider, sink).generate(request)

    assert provider.requests == []
    assert sink.events[0].error_code == "invalid_response_schema"


@pytest.mark.asyncio
async def test_output_that_breaks_contract_is_rejected() -> None:
    request = make_request()
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {request.id: FakeStructuredFixture(output={"unexpected": True})},
    )
    sink = InMemoryAIObservabilitySink()

    with pytest.raises(InvalidStructuredOutputError):
        await make_service(provider, sink).generate(request)

    assert sink.events[0].error_code == "invalid_structured_output"


@pytest.mark.asyncio
async def test_known_provider_error_is_propagated_with_safe_observability_code() -> None:
    request = make_request()
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {request.id: FakeStructuredFixture(error=ProviderUnavailableError())},
    )
    sink = InMemoryAIObservabilitySink()

    with pytest.raises(ProviderUnavailableError):
        await make_service(provider, sink).generate(request)

    assert sink.events[0].error_code == "provider_unavailable"


@pytest.mark.asyncio
async def test_unknown_provider_error_is_replaced_by_safe_domain_error() -> None:
    request = make_request()
    provider = StubProvider(make_provider_info(), error=RuntimeError("secret payload"))
    sink = InMemoryAIObservabilitySink()

    with pytest.raises(ProviderExecutionError) as captured:
        await make_service(provider, sink).generate(request)

    assert str(captured.value) == ""
    assert "secret payload" not in str(captured.value)
    assert sink.events[0].error_code == "provider_execution_error"


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["request_id", "provider", "model"])
async def test_provider_response_identity_must_match_request_and_adapter(
    mismatch: str,
) -> None:
    request = make_request(consent=ProcessingConsent(allow_cloud=True))
    response = make_response(
        request,
        request_id=uuid4() if mismatch == "request_id" else request.id,
        provider="other" if mismatch == "provider" else "fake",
        model="other" if mismatch == "model" else "fake-structured-v1",
    )
    provider = StubProvider(make_provider_info(), response=response)
    sink = InMemoryAIObservabilitySink()

    with pytest.raises(ProviderResponseMismatchError):
        await make_service(provider, sink).generate(request)

    assert sink.events[0].error_code == "provider_response_mismatch"


@pytest.mark.asyncio
async def test_service_defaults_are_usable() -> None:
    request = make_request()
    provider = FakeStructuredLLMProvider(
        make_provider_info(),
        {request.id: FakeStructuredFixture(output=valid_output())},
    )
    sink = InMemoryAIObservabilitySink()

    response = await StructuredGenerationService(provider, sink).generate(request)

    assert response.request_id == request.id
    assert sink.events[0].occurred_at.tzinfo is not None
