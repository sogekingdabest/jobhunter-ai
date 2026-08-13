"""Privacy-gated, observable structured generation use case."""

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from jobhunter.ai.domain.errors import (
    AIError,
    InvalidResponseSchemaError,
    InvalidStructuredOutputError,
    PrivacyPolicyViolationError,
    ProviderExecutionError,
    ProviderResponseMismatchError,
)
from jobhunter.ai.domain.observability import AIInvocationEvent, InvocationOutcome
from jobhunter.ai.domain.privacy import AIPrivacyPolicy
from jobhunter.ai.domain.types import (
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TokenUsage,
)
from jobhunter.ai.ports.llm import StructuredLLMProvider
from jobhunter.ai.ports.observability import AIObservabilitySink


class StructuredGenerationService:
    """Enforce policy and schema validation around an interchangeable provider."""

    def __init__(
        self,
        provider: StructuredLLMProvider,
        observability: AIObservabilitySink,
        *,
        privacy_policy: AIPrivacyPolicy | None = None,
        monotonic_clock: Callable[[], float] = perf_counter,
        wall_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._provider = provider
        self._observability = observability
        self._privacy_policy = privacy_policy or AIPrivacyPolicy()
        self._monotonic_clock = monotonic_clock
        self._wall_clock = wall_clock or (lambda: datetime.now(UTC))

    async def generate(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        """Authorize, execute, validate, and record one model invocation."""

        started_at = self._monotonic_clock()
        try:
            self._privacy_policy.authorize(request, self._provider.info)
        except PrivacyPolicyViolationError as error:
            self._record(request, started_at, InvocationOutcome.BLOCKED, error_code=error.code)
            raise

        try:
            Draft202012Validator.check_schema(request.response_schema)
            validator = Draft202012Validator(request.response_schema)
            response = await self._provider.generate_structured(request)
            self._validate_response_identity(request, response)
            validator.validate(response.output)
        except SchemaError as error:
            schema_error = InvalidResponseSchemaError()
            self._record(
                request, started_at, InvocationOutcome.FAILURE, error_code=schema_error.code
            )
            raise schema_error from error
        except ValidationError as error:
            output_error = InvalidStructuredOutputError()
            self._record(
                request, started_at, InvocationOutcome.FAILURE, error_code=output_error.code
            )
            raise output_error from error
        except AIError as error:
            self._record(request, started_at, InvocationOutcome.FAILURE, error_code=error.code)
            raise
        except Exception as error:
            provider_error = ProviderExecutionError()
            self._record(
                request, started_at, InvocationOutcome.FAILURE, error_code=provider_error.code
            )
            raise provider_error from error

        self._record(
            request,
            started_at,
            InvocationOutcome.SUCCESS,
            usage=response.usage,
        )
        return response

    def _validate_response_identity(
        self,
        request: StructuredGenerationRequest,
        response: StructuredGenerationResponse,
    ) -> None:
        provider = self._provider.info
        if (
            response.request_id != request.id
            or response.provider != provider.provider
            or response.model != provider.model
        ):
            raise ProviderResponseMismatchError

    def _record(
        self,
        request: StructuredGenerationRequest,
        started_at: float,
        outcome: InvocationOutcome,
        *,
        usage: TokenUsage | None = None,
        error_code: str | None = None,
    ) -> None:
        self._observability.record(
            AIInvocationEvent(
                occurred_at=self._wall_clock(),
                request_id=request.id,
                task=request.task,
                provider=self._provider.info.provider,
                model=self._provider.info.model,
                execution_location=self._provider.info.execution_location,
                outcome=outcome,
                duration_ms=(self._monotonic_clock() - started_at) * 1_000,
                input_count=len(request.inputs),
                usage=usage,
                error_code=error_code,
            )
        )
