"""Stable errors exposed by provider-neutral AI services."""


class AIError(Exception):
    """Base error with a safe categorical observability code."""

    code = "ai_error"


class PrivacyPolicyViolationError(AIError):
    """Raised before inference when explicit processing consent is missing."""

    code = "privacy_policy_violation"


class InvalidResponseSchemaError(AIError):
    """Raised when application code supplies an invalid JSON Schema."""

    code = "invalid_response_schema"


class InvalidStructuredOutputError(AIError):
    """Raised when provider output does not satisfy the requested schema."""

    code = "invalid_structured_output"


class ProviderUnavailableError(AIError):
    """Raised when the selected provider cannot complete a request."""

    code = "provider_unavailable"


class ProviderExecutionError(AIError):
    """Wrap unexpected provider failures without exposing sensitive details."""

    code = "provider_execution_error"


class ProviderResponseMismatchError(AIError):
    """Raised when response identity does not match its request or adapter."""

    code = "provider_response_mismatch"
