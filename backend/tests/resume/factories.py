"""Reusable tailored resume fixtures."""

from datetime import UTC, datetime
from uuid import uuid4

from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from jobhunter.resume.domain.models import (
    GenerationMethod,
    ResumeFragment,
    ResumeSection,
    ResumeSource,
    ResumeSourceType,
    ResumeStatus,
    TailoredResume,
)
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer

NOW = datetime(2026, 8, 14, 10, tzinfo=UTC)


def make_resume() -> TailoredResume:
    candidate = make_profile()
    offer = make_offer()
    assessment = StructuredMatchingPolicy().assess(candidate, offer, assessed_at=NOW)
    resume_id = uuid4()
    return TailoredResume(
        id=resume_id,
        candidate_profile_id=candidate.id,
        job_offer_id=offer.id,
        match_assessment_id=assessment.id,
        generation_version="tailored-resume-v1",
        candidate_updated_at=candidate.updated_at,
        job_content_fingerprint=offer.content_fingerprint,
        status=ResumeStatus.NEEDS_REVIEW,
        fragments=(
            ResumeFragment(
                id=uuid4(),
                resume_id=resume_id,
                section=ResumeSection.HEADER,
                position=0,
                generated_text=candidate.full_name,
                method=GenerationMethod.EXTRACTIVE,
                sources=(
                    ResumeSource(
                        id=uuid4(),
                        source_type=ResumeSourceType.PROFILE,
                        source_id=candidate.id,
                        evidence_source_id=candidate.evidence_source_id,
                        source_text=candidate.full_name,
                    ),
                ),
            ),
        ),
        created_at=NOW,
    )
