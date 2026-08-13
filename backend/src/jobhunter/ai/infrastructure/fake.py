"""Deterministic adapters for tests, demos, and offline evaluation."""

from copy import deepcopy
from dataclasses import dataclass
from uuid import UUID

from jobhunter.ai.domain.errors import AIError, ProviderUnavailableError
from jobhunter.ai.domain.observability import AIInvocationEvent
from jobhunter.ai.domain.types import (
    FinishReason,
    JSONObject,
    ProviderInfo,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TokenUsage,
)


@dataclass(frozen=True, slots=True)
class FakeStructuredFixture:
    """One predetermined response or safe domain error."""

    output: JSONObject | None = None
    error: AIError | None = None
    finish_reason: FinishReason = FinishReason.COMPLETE
    usage: TokenUsage | None = None

    def __post_init__(self) -> None:
        if (self.output is None) == (self.error is None):
            raise ValueError("fake_fixture_requires_one_outcome")


class FakeStructuredLLMProvider:
    """Return fixtures by request ID without network access or hidden behavior."""

    def __init__(
        self,
        info: ProviderInfo,
        fixtures: dict[UUID, FakeStructuredFixture],
    ) -> None:
        self._info = info
        self._fixtures = dict(fixtures)
        self.requests: list[StructuredGenerationRequest] = []

    @property
    def info(self) -> ProviderInfo:
        return self._info

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        self.requests.append(request)
        fixture = self._fixtures.get(request.id)
        if fixture is None:
            raise ProviderUnavailableError
        if fixture.error is not None:
            raise fixture.error
        if fixture.output is None:  # pragma: no cover - guarded by fixture invariant
            raise RuntimeError("invalid_fake_fixture")
        return StructuredGenerationResponse(
            request_id=request.id,
            provider=self.info.provider,
            model=self.info.model,
            output=deepcopy(fixture.output),
            finish_reason=fixture.finish_reason,
            usage=fixture.usage,
        )


class InMemoryAIObservabilitySink:
    """Collect privacy-safe events for tests and local demonstrations."""

    def __init__(self) -> None:
        self.events: list[AIInvocationEvent] = []

    def record(self, event: AIInvocationEvent) -> None:
        self.events.append(event)
