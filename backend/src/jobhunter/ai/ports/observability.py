"""Port for content-free AI invocation telemetry."""

from typing import Protocol

from jobhunter.ai.domain.observability import AIInvocationEvent


class AIObservabilitySink(Protocol):  # pragma: no cover - structural typing contract
    """Record invocation metadata without prompts, inputs, or model output."""

    def record(self, event: AIInvocationEvent) -> None:
        """Persist or export one privacy-safe event."""
