"""Tests for provider-neutral request and response invariants."""

from collections.abc import Callable
from uuid import uuid4

import pytest

from jobhunter.ai.domain.types import (
    DataClassification,
    ExecutionLocation,
    FinishReason,
    InputTrust,
    ModelInput,
    ProviderInfo,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TokenUsage,
)
from tests.ai.factories import make_request, valid_output


@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (lambda: ModelInput("Bad name", "text", InputTrust.USER_PROVIDED), "invalid_input_name"),
        (lambda: ModelInput("cv_text", " ", InputTrust.USER_PROVIDED), "missing_input_content"),
        (
            lambda: ProviderInfo(" ", "model", ExecutionLocation.LOCAL),
            "missing_provider",
        ),
        (
            lambda: ProviderInfo("provider", " ", ExecutionLocation.LOCAL),
            "missing_model",
        ),
        (lambda: TokenUsage(-1, 0), "invalid_token_usage"),
        (lambda: TokenUsage(0, -1), "invalid_token_usage"),
    ],
)
def test_value_objects_reject_invalid_values(factory: Callable[[], object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        factory()


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"task": "Bad task"}, "invalid_task"),
        ({"instruction": " "}, "missing_instruction"),
        ({"inputs": ()}, "missing_model_inputs"),
        (
            {
                "inputs": (
                    ModelInput("cv_text", "one", InputTrust.USER_PROVIDED),
                    ModelInput("cv_text", "two", InputTrust.UNTRUSTED_EXTERNAL),
                )
            },
            "duplicate_model_input",
        ),
        ({"response_schema": {}}, "missing_response_schema"),
        ({"max_output_tokens": 0}, "invalid_max_output_tokens"),
        ({"temperature": -0.1}, "invalid_temperature"),
        ({"temperature": 2.1}, "invalid_temperature"),
    ],
)
def test_request_rejects_invalid_values(change: dict[str, object], expected: str) -> None:
    request = make_request()
    values = {field: getattr(request, field) for field in request.__dataclass_fields__}
    values.update(change)

    with pytest.raises(ValueError, match=expected):
        StructuredGenerationRequest(**values)


@pytest.mark.parametrize(("provider", "model"), [(" ", "model"), ("provider", " ")])
def test_response_requires_provider_identity(provider: str, model: str) -> None:
    expected = "missing_provider" if not provider.strip() else "missing_model"
    with pytest.raises(ValueError, match=expected):
        StructuredGenerationResponse(
            request_id=uuid4(),
            provider=provider,
            model=model,
            output=valid_output(),
            finish_reason=FinishReason.COMPLETE,
        )


def test_valid_request_and_response_are_immutable_value_objects() -> None:
    request = make_request()
    response = StructuredGenerationResponse(
        request_id=request.id,
        provider="fake",
        model="model",
        output=valid_output(),
        finish_reason=FinishReason.LENGTH,
        usage=TokenUsage(1, 2),
    )

    assert request.data_classification is DataClassification.PERSONAL
    assert response.usage == TokenUsage(1, 2)
