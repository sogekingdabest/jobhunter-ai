"""Privacy-safe AI invocation telemetry."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from jobhunter.ai.domain.types import ExecutionLocation, TokenUsage


class InvocationOutcome(StrEnum):
    """High-level outcome suitable for metrics without model content."""

    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class AIInvocationEvent:
    """Metadata-only event that intentionally cannot hold prompts or outputs."""

    occurred_at: datetime
    request_id: UUID
    task: str
    provider: str
    model: str
    execution_location: ExecutionLocation
    outcome: InvocationOutcome
    duration_ms: float
    input_count: int
    usage: TokenUsage | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("naive_observability_timestamp")
        if self.duration_ms < 0:
            raise ValueError("invalid_invocation_duration")
        if self.input_count <= 0:
            raise ValueError("invalid_input_count")
        failed = self.outcome is not InvocationOutcome.SUCCESS
        if failed != (self.error_code is not None):
            raise ValueError("invalid_invocation_error_code")
        if failed and self.usage is not None:
            raise ValueError("unexpected_failed_usage")
