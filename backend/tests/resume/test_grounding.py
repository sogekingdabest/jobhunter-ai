"""Conservative rewrite grounding tests."""

from uuid import UUID, uuid4

import pytest

from jobhunter.resume.domain.grounding import UngroundedResumeOutputError, validate_rewrites
from jobhunter.resume.domain.models import ResumeSection, ResumeSourceType
from jobhunter.resume.domain.selection import ResumeSelection


def selection(text: str = "Designed Python APIs") -> ResumeSelection:
    return ResumeSelection(
        uuid4(), ResumeSection.EXPERIENCE, ResumeSourceType.WORK_EXPERIENCE, uuid4(), uuid4(), text
    )


def test_rewrite_can_reorder_source_words_and_add_connectors() -> None:
    item = selection()

    validate_rewrites((item,), {item.id: "Python APIs designed with"})


@pytest.mark.parametrize(
    ("rewrites", "error"),
    [
        ({}, "resume_rewrite_selection_mismatch"),
        ({uuid4(): "Python"}, "resume_rewrite_selection_mismatch"),
    ],
)
def test_rewrite_requires_exact_selection_set(rewrites: dict[UUID, str], error: str) -> None:
    with pytest.raises(UngroundedResumeOutputError, match=error):
        validate_rewrites((selection(),), rewrites)


def test_rewrite_rejects_empty_text() -> None:
    item = selection()
    with pytest.raises(UngroundedResumeOutputError, match="empty_resume_rewrite"):
        validate_rewrites((item,), {item.id: " "})


def test_rewrite_rejects_skill_copied_only_from_job_offer() -> None:
    item = selection()
    with pytest.raises(UngroundedResumeOutputError, match="unsupported_resume_claim"):
        validate_rewrites((item,), {item.id: "Designed Python and Kubernetes APIs"})


def test_grounding_is_case_and_punctuation_insensitive() -> None:
    item = selection("Python 3.12 | C++")
    validate_rewrites((item,), {item.id: "c++ and PYTHON 3.12."})
