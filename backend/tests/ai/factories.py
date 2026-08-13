"""Reusable fictional AI contract fixtures."""

from uuid import UUID, uuid4

from jobhunter.ai.contracts.candidate_facts import candidate_fact_extraction_schema
from jobhunter.ai.domain.types import (
    DataClassification,
    ExecutionLocation,
    FinishReason,
    InputTrust,
    JSONObject,
    ModelInput,
    ProcessingConsent,
    ProviderInfo,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TokenUsage,
)

FICTIONAL_SOURCE = (
    "Alex Example worked as a Backend Engineer at Example Robotics. Built APIs with Python and SQL."
)


def valid_output() -> JSONObject:
    return {
        "contract_version": "1.0",
        "facts": [
            {
                "fact_type": "competency",
                "value": "Python",
                "evidence": {
                    "quote": "Python",
                    "start_offset": 81,
                    "end_offset": 87,
                    "page_number": None,
                },
                "confidence": 0.99,
            }
        ],
        "warnings": [],
    }


def make_request(
    *,
    request_id: UUID | None = None,
    consent: ProcessingConsent | None = None,
    response_schema: JSONObject | None = None,
) -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        id=request_id or uuid4(),
        task="candidate_fact_extraction",
        instruction="Extract only facts supported by exact evidence quotes.",
        inputs=(ModelInput("cv_text", FICTIONAL_SOURCE, InputTrust.USER_PROVIDED),),
        response_schema=response_schema or candidate_fact_extraction_schema(),
        data_classification=DataClassification.PERSONAL,
        consent=consent or ProcessingConsent(),
    )


def make_provider_info(
    *,
    execution_location: ExecutionLocation = ExecutionLocation.LOCAL,
    retains_inputs: bool = False,
    uses_inputs_for_training: bool = False,
) -> ProviderInfo:
    return ProviderInfo(
        provider="fake",
        model="fake-structured-v1",
        execution_location=execution_location,
        retains_inputs=retains_inputs,
        uses_inputs_for_training=uses_inputs_for_training,
    )


def make_response(
    request: StructuredGenerationRequest,
    *,
    output: JSONObject | None = None,
    request_id: UUID | None = None,
    provider: str = "fake",
    model: str = "fake-structured-v1",
) -> StructuredGenerationResponse:
    return StructuredGenerationResponse(
        request_id=request_id or request.id,
        provider=provider,
        model=model,
        output=output or valid_output(),
        finish_reason=FinishReason.COMPLETE,
        usage=TokenUsage(100, 25),
    )
