"""Conservative deterministic validation for model-authored resume text."""

import re
from collections.abc import Mapping
from uuid import UUID

from jobhunter.resume.domain.selection import ResumeSelection

TOKEN_PATTERN = re.compile(r"[\w+#.]+", re.UNICODE)
SAFE_CONNECTORS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "de",
        "del",
        "el",
        "en",
        "for",
        "in",
        "la",
        "las",
        "los",
        "of",
        "para",
        "the",
        "to",
        "un",
        "una",
        "with",
        "y",
    }
)


class UngroundedResumeOutputError(ValueError):
    """Model output contains an unknown selection or unsupported content term."""


def validate_rewrites(
    selections: tuple[ResumeSelection, ...], rewrites: Mapping[UUID, str]
) -> None:
    expected = {selection.id for selection in selections}
    if set(rewrites) != expected:
        raise UngroundedResumeOutputError("resume_rewrite_selection_mismatch")
    for selection in selections:
        text = rewrites[selection.id]
        if not text.strip():
            raise UngroundedResumeOutputError("empty_resume_rewrite")
        source_tokens = {
            _normalize(token) for token in TOKEN_PATTERN.findall(selection.source_text)
        }
        generated_tokens = {_normalize(token) for token in TOKEN_PATTERN.findall(text)}
        unsupported = generated_tokens - source_tokens - SAFE_CONNECTORS
        if unsupported:
            raise UngroundedResumeOutputError("unsupported_resume_claim")


def _normalize(token: str) -> str:
    return token.casefold().strip(".")
