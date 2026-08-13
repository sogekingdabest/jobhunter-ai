"""Candidate fact proposal contract for the later CV extraction workflow."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from jobhunter.ai.domain.types import JSONObject
from jobhunter.candidate.domain.facts import CandidateFactType


class ContractModel(BaseModel):
    """Strict base for versioned provider output."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceCandidate(ContractModel):
    """Exact source text proposed as evidence for a candidate fact."""

    quote: Annotated[str, Field(min_length=1, max_length=2_000)]
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(gt=0)]
    page_number: Annotated[int, Field(gt=0)] | None = None

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceCandidate":
        if self.end_offset <= self.start_offset:
            raise ValueError("invalid_evidence_offsets")
        return self


class CandidateFactProposal(ContractModel):
    """Untrusted model proposal that is not accepted into the master CV automatically."""

    fact_type: CandidateFactType
    value: Annotated[str, Field(min_length=1, max_length=2_000)]
    evidence: EvidenceCandidate
    confidence: Annotated[float, Field(ge=0, le=1)]


class CandidateFactExtractionOutput(ContractModel):
    """Version 1 output for proposed candidate facts and non-sensitive warnings."""

    contract_version: Annotated[str, Field(pattern=r"^1\.0$")]
    facts: Annotated[list[CandidateFactProposal], Field(max_length=200)]
    warnings: Annotated[list[str], Field(max_length=50)] = Field(default_factory=list)


def candidate_fact_extraction_schema() -> JSONObject:
    """Return a JSON Schema 2020-12 document for provider structured output."""

    schema = CandidateFactExtractionOutput.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:jobhunter-ai:ai:candidate-fact-extraction:1.0"
    return schema
