"""Tests for versioned candidate-fact structured output."""

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from jobhunter.ai.contracts.candidate_facts import (
    CandidateFactExtractionOutput,
    EvidenceCandidate,
    candidate_fact_extraction_schema,
)
from tests.ai.factories import valid_output


def test_candidate_fact_contract_and_schema_accept_supported_output() -> None:
    output = CandidateFactExtractionOutput.model_validate(valid_output())
    schema = candidate_fact_extraction_schema()

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(output.model_dump(mode="json"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert output.facts[0].evidence.quote == "Python"


def test_candidate_fact_contract_rejects_unknown_or_unversioned_output() -> None:
    invalid = valid_output()
    invalid["invented_field"] = True

    with pytest.raises(ValidationError):
        CandidateFactExtractionOutput.model_validate(invalid)

    invalid = valid_output()
    invalid["contract_version"] = "2.0"
    with pytest.raises(ValidationError):
        CandidateFactExtractionOutput.model_validate(invalid)


def test_evidence_candidate_rejects_reversed_offsets() -> None:
    with pytest.raises(ValidationError, match="invalid_evidence_offsets"):
        EvidenceCandidate(quote="Python", start_offset=10, end_offset=5)
