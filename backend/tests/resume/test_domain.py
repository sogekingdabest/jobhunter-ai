"""Tailored resume aggregate invariants."""

from dataclasses import replace
from uuid import uuid4

import pytest

from jobhunter.resume.domain.models import (
    GenerationMethod,
    ResumeStatus,
)
from tests.resume.factories import NOW, make_resume


def test_resume_can_be_approved_once() -> None:
    resume = make_resume()

    approved = resume.review(ResumeStatus.APPROVED, reviewed_at=NOW)

    assert approved.status is ResumeStatus.APPROVED
    assert approved.reviewed_at == NOW
    assert approved.revision == 1
    with pytest.raises(ValueError, match="resume_already_reviewed"):
        approved.review(ResumeStatus.REJECTED, reviewed_at=NOW)
    with pytest.raises(ValueError, match="invalid_resume_review_decision"):
        resume.review(ResumeStatus.NEEDS_REVIEW, reviewed_at=NOW)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"generation_version": " "}, "missing_resume_generation_version"),
        ({"job_content_fingerprint": "short"}, "invalid_resume_job_fingerprint"),
        ({"revision": -1}, "invalid_resume_revision"),
        ({"fragments": ()}, "empty_tailored_resume"),
        ({"reviewed_at": NOW}, "invalid_resume_review_state"),
    ],
)
def test_resume_rejects_invalid_state(changes: dict[str, object], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        replace(make_resume(), **changes)  # type: ignore[arg-type]


def test_resume_rejects_foreign_or_misordered_fragments_and_provider_mismatch() -> None:
    resume = make_resume()
    fragment = resume.fragments[0]
    with pytest.raises(ValueError, match="foreign_resume_fragment"):
        replace(resume, fragments=(replace(fragment, resume_id=uuid4()),))
    with pytest.raises(ValueError, match="invalid_resume_fragment_order"):
        replace(resume, fragments=(replace(fragment, position=1),))
    with pytest.raises(ValueError, match="inconsistent_resume_provider_metadata"):
        replace(
            resume,
            fragments=(replace(fragment, method=GenerationMethod.LLM_REPHRASED),),
        )
    with pytest.raises(ValueError, match="inconsistent_resume_provider_metadata"):
        replace(resume, provider="fake", model="model")


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"position": -1}, "invalid_resume_fragment_position"),
        ({"generated_text": " "}, "missing_resume_fragment_text"),
        ({"sources": ()}, "ungrounded_resume_fragment"),
    ],
)
def test_fragment_rejects_invalid_state(changes: dict[str, object], error: str) -> None:
    fragment = make_resume().fragments[0]
    with pytest.raises(ValueError, match=error):
        replace(fragment, **changes)  # type: ignore[arg-type]


def test_fragment_rejects_duplicate_sources() -> None:
    fragment = make_resume().fragments[0]
    with pytest.raises(ValueError, match="duplicate_resume_source"):
        replace(fragment, sources=(fragment.sources[0], fragment.sources[0]))


def test_source_requires_text() -> None:
    source = make_resume().fragments[0].sources[0]
    with pytest.raises(ValueError, match="missing_resume_source_text"):
        replace(source, source_text=" ")
