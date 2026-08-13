"""Tests for content-free AI invocation events."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from jobhunter.ai.domain.observability import AIInvocationEvent, InvocationOutcome
from jobhunter.ai.domain.types import ExecutionLocation, TokenUsage


def event(**changes: object) -> AIInvocationEvent:
    base = AIInvocationEvent(
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        request_id=uuid4(),
        task="candidate_fact_extraction",
        provider="fake",
        model="fake-v1",
        execution_location=ExecutionLocation.LOCAL,
        outcome=InvocationOutcome.SUCCESS,
        duration_ms=10.0,
        input_count=1,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (
            lambda: event(occurred_at=datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None)),
            "naive_observability_timestamp",
        ),
        (lambda: event(duration_ms=-1), "invalid_invocation_duration"),
        (lambda: event(input_count=0), "invalid_input_count"),
        (lambda: event(error_code="unexpected"), "invalid_invocation_error_code"),
        (
            lambda: event(outcome=InvocationOutcome.FAILURE),
            "invalid_invocation_error_code",
        ),
        (
            lambda: event(
                outcome=InvocationOutcome.FAILURE,
                error_code="safe_code",
                usage=TokenUsage(1, 1),
            ),
            "unexpected_failed_usage",
        ),
    ],
)
def test_event_rejects_invalid_metadata(factory: Callable[[], object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        factory()


def test_event_shape_cannot_contain_model_content() -> None:
    recorded = event(usage=TokenUsage(10, 2))

    assert recorded.outcome is InvocationOutcome.SUCCESS
    assert not hasattr(recorded, "prompt")
    assert not hasattr(recorded, "input_content")
    assert not hasattr(recorded, "output")
