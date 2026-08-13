"""Strict provider-neutral output contract for job offer normalization."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from jobhunter.ai.domain.types import JSONObject
from jobhunter.jobs.domain.offers import (
    EmploymentType,
    JobFieldName,
    RemoteType,
    RequirementPriority,
    RequirementType,
    Seniority,
)


class JobContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobEvidenceCandidate(JobContractModel):
    quote: Annotated[str, Field(min_length=1, max_length=10_000)]
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def validate_offsets(self) -> "JobEvidenceCandidate":
        if self.end_offset <= self.start_offset:
            raise ValueError("invalid_job_evidence_offsets")
        return self


class GroundedJobValue[ValueT](JobContractModel):
    value: ValueT
    evidence: JobEvidenceCandidate
    confidence: Annotated[float, Field(ge=0, le=1)]


class JobRequirementCandidate(JobContractModel):
    requirement_type: RequirementType
    priority: RequirementPriority
    normalized_value: Annotated[str, Field(min_length=1, max_length=2_000)]
    evidence: JobEvidenceCandidate
    confidence: Annotated[float, Field(ge=0, le=1)]


class JobOfferNormalizationOutput(JobContractModel):
    """Versioned normalized facts; all values require exact source evidence."""

    contract_version: Annotated[str, Field(pattern=r"^1\.0$")]
    company: GroundedJobValue[Annotated[str, Field(min_length=1, max_length=300)]] | None = None
    title: GroundedJobValue[Annotated[str, Field(min_length=1, max_length=300)]] | None = None
    location: GroundedJobValue[Annotated[str, Field(min_length=1, max_length=300)]] | None = None
    remote_type: GroundedJobValue[RemoteType] | None = None
    employment_type: GroundedJobValue[EmploymentType] | None = None
    seniority: GroundedJobValue[Seniority] | None = None
    requirements: Annotated[list[JobRequirementCandidate], Field(max_length=300)]
    warnings: Annotated[list[str], Field(max_length=50)] = Field(default_factory=list)

    def field_candidates(self) -> tuple[tuple[JobFieldName, GroundedJobValue[Any]], ...]:
        """Expose present scalar fields uniformly to the application layer."""

        values: list[tuple[JobFieldName, GroundedJobValue[Any]]] = []
        for name in JobFieldName:
            candidate = getattr(self, name.value)
            if candidate is not None:
                values.append((name, candidate))
        return tuple(values)


def job_offer_normalization_schema() -> JSONObject:
    """Return JSON Schema 2020-12 for browser, local, or cloud inference."""

    schema = JobOfferNormalizationOutput.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "urn:jobhunter-ai:ai:job-offer-normalization:1.0"
    return schema
