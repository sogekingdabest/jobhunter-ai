"""Provider-neutral structured generation port."""

from typing import Protocol

from jobhunter.ai.domain.types import (
    ProviderInfo,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)


class StructuredLLMProvider(Protocol):  # pragma: no cover - structural typing contract
    """Generate JSON-compatible output without exposing an SDK to the application."""

    @property
    def info(self) -> ProviderInfo:
        """Describe model identity and privacy behavior."""

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        """Execute one structured generation request."""
