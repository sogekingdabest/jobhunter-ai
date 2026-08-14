"""Deterministic resume selection tests."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

from jobhunter.matching.domain.policy import StructuredMatchingPolicy
from jobhunter.resume.domain.models import ResumeSection
from jobhunter.resume.domain.selection import select_resume_facts
from tests.candidate.factories import make_profile
from tests.jobs.factories import make_offer
from tests.resume.factories import NOW

EXPECTED_MINIMAL_SELECTIONS = 2
MAX_EXPERIENCE_SELECTIONS = 4


def test_selection_builds_ordered_source_snapshots_without_contact_data() -> None:
    candidate = make_profile()
    offer = make_offer()
    assessment = StructuredMatchingPolicy().assess(candidate, offer, assessed_at=NOW)

    selections = select_resume_facts(candidate, assessment)

    assert candidate.email is not None
    assert candidate.phone is not None
    assert selections[0].section is ResumeSection.HEADER
    assert candidate.email not in selections[0].source_text
    assert candidate.phone not in selections[0].source_text
    assert [item.section for item in selections] == [
        ResumeSection.HEADER,
        ResumeSection.SUMMARY,
        ResumeSection.EXPERIENCE,
        ResumeSection.EDUCATION,
        ResumeSection.PROJECTS,
        ResumeSection.SKILLS,
        ResumeSection.LANGUAGES,
    ]
    assert "2023-01-01 - present" in selections[2].source_text


def test_selection_omits_optional_profile_text_and_handles_unknown_dates() -> None:
    candidate = make_profile()
    experience = replace(candidate.work_experiences[0], start_date=None, end_date=date(2025, 1, 1))
    candidate = replace(
        candidate,
        headline=None,
        summary=None,
        location=None,
        work_experiences=(experience,),
        education=(),
        projects=(),
        competencies=(),
        languages=(),
    )
    assessment = StructuredMatchingPolicy().assess(candidate, make_offer(), assessed_at=NOW)

    selections = select_resume_facts(candidate, assessment)

    assert len(selections) == EXPECTED_MINIMAL_SELECTIONS
    assert selections[0].source_text == candidate.full_name
    assert "? - 2025-01-01" in selections[1].source_text

    without_dates = replace(experience, start_date=None, end_date=None)
    candidate = replace(candidate, work_experiences=(without_dates,))
    assessment = StructuredMatchingPolicy().assess(candidate, make_offer(), assessed_at=NOW)
    selections = select_resume_facts(candidate, assessment)
    assert "?" not in selections[1].source_text


def test_selection_limits_experience_entries() -> None:
    candidate = make_profile()
    template = candidate.work_experiences[0]
    experiences = tuple(
        replace(
            template,
            id=template.id if index == 0 else uuid4(),
            title=f"Role {index}",
        )
        for index in range(6)
    )
    candidate = replace(candidate, work_experiences=experiences)
    assessment = StructuredMatchingPolicy().assess(candidate, make_offer(), assessed_at=NOW)

    selections = select_resume_facts(candidate, assessment)

    assert (
        sum(item.section is ResumeSection.EXPERIENCE for item in selections)
        == MAX_EXPERIENCE_SELECTIONS
    )
