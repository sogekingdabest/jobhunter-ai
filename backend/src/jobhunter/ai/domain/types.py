"""Provider-neutral structured generation values."""

import re
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

type JSONScalar = str | int | float | bool | None
type JSONValue = JSONScalar | list[JSONValue] | dict[str, JSONValue]
type JSONObject = dict[str, JSONValue]
TASK_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
MAX_TEMPERATURE = 2.0


class DataClassification(StrEnum):
    """Highest sensitivity present in a model request."""

    PUBLIC = "public"
    PERSONAL = "personal"
    SENSITIVE_PERSONAL = "sensitive_personal"


class InputTrust(StrEnum):
    """Whether model input is candidate data or untrusted external content."""

    USER_PROVIDED = "user_provided"
    UNTRUSTED_EXTERNAL = "untrusted_external"


class ExecutionLocation(StrEnum):
    """Where inference bytes are processed."""

    BROWSER = "browser"
    LOCAL = "local"
    CLOUD = "cloud"


class FinishReason(StrEnum):
    """Provider-neutral completion reason."""

    COMPLETE = "complete"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"


@dataclass(frozen=True, slots=True)
class ModelInput:
    """Named data supplied to a trusted, code-owned instruction."""

    name: str
    content: str
    trust: InputTrust

    def __post_init__(self) -> None:
        if not TASK_PATTERN.fullmatch(self.name):
            raise ValueError("invalid_input_name")
        if not self.content.strip():
            raise ValueError("missing_input_content")


@dataclass(frozen=True, slots=True)
class ProcessingConsent:
    """Explicit permissions for processing outside the user's device."""

    allow_cloud: bool = False
    allow_input_retention: bool = False
    allow_training: bool = False


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """Privacy and identity metadata declared by an LLM adapter."""

    provider: str
    model: str
    execution_location: ExecutionLocation
    retains_inputs: bool = False
    uses_inputs_for_training: bool = False

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("missing_provider")
        if not self.model.strip():
            raise ValueError("missing_model")


@dataclass(frozen=True, slots=True)
class StructuredGenerationRequest:
    """Structured inference request with trusted instructions separated from data."""

    id: UUID
    task: str
    instruction: str
    inputs: tuple[ModelInput, ...]
    response_schema: JSONObject
    data_classification: DataClassification
    consent: ProcessingConsent = field(default_factory=ProcessingConsent)
    max_output_tokens: int = 2_048
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if not TASK_PATTERN.fullmatch(self.task):
            raise ValueError("invalid_task")
        if not self.instruction.strip():
            raise ValueError("missing_instruction")
        if not self.inputs:
            raise ValueError("missing_model_inputs")
        names = tuple(model_input.name for model_input in self.inputs)
        if len(names) != len(set(names)):
            raise ValueError("duplicate_model_input")
        if not self.response_schema:
            raise ValueError("missing_response_schema")
        if self.max_output_tokens <= 0:
            raise ValueError("invalid_max_output_tokens")
        if not 0 <= self.temperature <= MAX_TEMPERATURE:
            raise ValueError("invalid_temperature")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Optional provider-reported token counts."""

    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("invalid_token_usage")


@dataclass(frozen=True, slots=True)
class StructuredGenerationResponse:
    """Validated JSON-compatible provider response and non-sensitive metadata."""

    request_id: UUID
    provider: str
    model: str
    output: JSONObject
    finish_reason: FinishReason
    usage: TokenUsage | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("missing_provider")
        if not self.model.strip():
            raise ValueError("missing_model")
