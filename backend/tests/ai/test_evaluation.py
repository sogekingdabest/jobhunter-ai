"""Tests for deterministic structured-output evaluation."""

import json
from pathlib import Path
from typing import cast

import pytest

from jobhunter.ai.contracts.candidate_facts import candidate_fact_extraction_schema
from jobhunter.ai.domain.errors import InvalidResponseSchemaError
from jobhunter.ai.domain.types import JSONObject
from jobhunter.ai.evaluation.metrics import (
    StructuredEvaluationCase,
    StructuredEvaluationReport,
    evaluate_structured_outputs,
)
from tests.ai.factories import FICTIONAL_SOURCE, valid_output

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "ai" / "candidate_fact_extraction.json"


def test_fictional_golden_fixture_scores_perfectly() -> None:
    fixture = cast(JSONObject, json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    case = StructuredEvaluationCase(
        case_id=cast(str, fixture["case_id"]),
        source_text=cast(str, fixture["source_text"]),
        expected=cast(JSONObject, fixture["expected"]),
        actual=cast(JSONObject, fixture["actual"]),
    )

    report = evaluate_structured_outputs(
        (case,), response_schema=candidate_fact_extraction_schema()
    )

    assert report == StructuredEvaluationReport(1, 1.0, 1.0, 1.0)


def test_metrics_report_invalid_mismatched_and_ungrounded_output() -> None:
    case = StructuredEvaluationCase(
        case_id="ungrounded",
        source_text=FICTIONAL_SOURCE,
        expected=valid_output(),
        actual={
            "contract_version": "1.0",
            "facts": [
                {
                    "fact_type": "competency",
                    "value": "Kubernetes",
                    "evidence": {
                        "quote": "Kubernetes",
                        "start_offset": 0,
                        "end_offset": 10,
                        "page_number": None,
                    },
                    "confidence": 0.7,
                }
            ],
            "warnings": [],
        },
    )

    report = evaluate_structured_outputs(
        (case,), response_schema=candidate_fact_extraction_schema()
    )

    assert report.schema_validity_rate == 1.0
    assert report.exact_match_rate == 0.0
    assert report.evidence_grounding_rate == 0.0


def test_output_without_non_empty_string_quotes_has_no_grounding_metric() -> None:
    case = StructuredEvaluationCase(
        case_id="invalid-shapes",
        source_text=FICTIONAL_SOURCE,
        expected=valid_output(),
        actual={"quote": 1, "nested": [{"quote": ""}], "scalar": True},
    )

    report = evaluate_structured_outputs(
        (case,), response_schema=candidate_fact_extraction_schema()
    )

    assert report.schema_validity_rate == 0.0
    assert report.exact_match_rate == 0.0
    assert report.evidence_grounding_rate is None


def test_evaluation_rejects_missing_cases_and_invalid_schema() -> None:
    with pytest.raises(ValueError, match="missing_evaluation_cases"):
        evaluate_structured_outputs((), response_schema={})

    case = StructuredEvaluationCase("case", FICTIONAL_SOURCE, valid_output(), valid_output())
    with pytest.raises(InvalidResponseSchemaError):
        evaluate_structured_outputs((case,), response_schema={"type": "not-a-json-schema-type"})


@pytest.mark.parametrize(
    ("case_id", "source", "error"),
    [
        (" ", FICTIONAL_SOURCE, "missing_evaluation_case_id"),
        ("case", " ", "missing_evaluation_source"),
    ],
)
def test_evaluation_case_invariants(case_id: str, source: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        StructuredEvaluationCase(case_id, source, valid_output(), valid_output())


@pytest.mark.parametrize(
    ("report", "error"),
    [
        ((0, 1.0, 1.0, 1.0), "invalid_evaluation_case_count"),
        ((1, -0.1, 1.0, 1.0), "invalid_evaluation_metric"),
        ((1, 1.0, 1.1, None), "invalid_evaluation_metric"),
        ((1, 1.0, 1.0, 2.0), "invalid_evaluation_metric"),
    ],
)
def test_evaluation_report_invariants(
    report: tuple[int, float, float, float | None],
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        StructuredEvaluationReport(*report)
