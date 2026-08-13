"""Schema, exact-match, and evidence-grounding metrics."""

import json
from dataclasses import dataclass

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from jobhunter.ai.domain.errors import InvalidResponseSchemaError
from jobhunter.ai.domain.types import JSONObject, JSONValue


@dataclass(frozen=True, slots=True)
class StructuredEvaluationCase:
    """One fictional expected/actual pair and its source text."""

    case_id: str
    source_text: str
    expected: JSONObject
    actual: JSONObject

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("missing_evaluation_case_id")
        if not self.source_text.strip():
            raise ValueError("missing_evaluation_source")


@dataclass(frozen=True, slots=True)
class StructuredEvaluationReport:
    """Aggregate deterministic metrics in the closed zero-to-one interval."""

    total_cases: int
    schema_validity_rate: float
    exact_match_rate: float
    evidence_grounding_rate: float | None

    def __post_init__(self) -> None:
        if self.total_cases <= 0:
            raise ValueError("invalid_evaluation_case_count")
        metrics = [self.schema_validity_rate, self.exact_match_rate]
        if self.evidence_grounding_rate is not None:
            metrics.append(self.evidence_grounding_rate)
        if any(not 0 <= metric <= 1 for metric in metrics):
            raise ValueError("invalid_evaluation_metric")


def evaluate_structured_outputs(
    cases: tuple[StructuredEvaluationCase, ...],
    *,
    response_schema: JSONObject,
) -> StructuredEvaluationReport:
    """Evaluate deterministic output without invoking or trusting an LLM judge."""

    if not cases:
        raise ValueError("missing_evaluation_cases")
    try:
        Draft202012Validator.check_schema(response_schema)
    except SchemaError as error:
        raise InvalidResponseSchemaError from error
    validator = Draft202012Validator(response_schema)

    valid_cases = 0
    exact_matches = 0
    grounded_quotes = 0
    total_quotes = 0
    for case in cases:
        if validator.is_valid(case.actual):
            valid_cases += 1
        if _canonical_json(case.actual) == _canonical_json(case.expected):
            exact_matches += 1
        quotes = tuple(_evidence_quotes(case.actual))
        total_quotes += len(quotes)
        grounded_quotes += sum(quote in case.source_text for quote in quotes)

    total = len(cases)
    return StructuredEvaluationReport(
        total_cases=total,
        schema_validity_rate=valid_cases / total,
        exact_match_rate=exact_matches / total,
        evidence_grounding_rate=grounded_quotes / total_quotes if total_quotes else None,
    )


def _canonical_json(value: JSONValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _evidence_quotes(value: JSONValue) -> list[str]:
    quotes: list[str] = []
    if isinstance(value, dict):
        quote = value.get("quote")
        if isinstance(quote, str) and quote:
            quotes.append(quote)
        for nested in value.values():
            quotes.extend(_evidence_quotes(nested))
    elif isinstance(value, list):
        for nested in value:
            quotes.extend(_evidence_quotes(nested))
    return quotes
