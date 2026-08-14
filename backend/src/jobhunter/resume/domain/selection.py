"""Deterministic candidate-fact selection for tailored resumes."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from jobhunter.candidate.domain.competencies import Competency, LanguageProficiency
from jobhunter.candidate.domain.experience import Education, Project, WorkExperience
from jobhunter.candidate.domain.profile import CandidateProfile
from jobhunter.matching.domain.assessments import MatchAssessment
from jobhunter.resume.domain.models import ResumeSection, ResumeSourceType

GENERATION_VERSION = "tailored-resume-v1"


@dataclass(frozen=True, slots=True)
class ResumeSelection:
    id: UUID
    section: ResumeSection
    source_type: ResumeSourceType
    source_id: UUID
    evidence_source_id: UUID
    source_text: str


def select_resume_facts(
    candidate: CandidateProfile, assessment: MatchAssessment
) -> tuple[ResumeSelection, ...]:
    """Select and order only facts owned by the master profile."""

    relevant = {
        fact_id
        for dimension in assessment.dimensions
        for evidence in dimension.evidence
        for fact_id in evidence.candidate_fact_ids
    }
    relevant.update(item.candidate_source_id for item in assessment.semantic_evidence)
    selected: list[ResumeSelection] = []

    header = " | ".join(
        value for value in (candidate.full_name, candidate.headline, candidate.location) if value
    )
    selected.append(_selection(candidate, ResumeSection.HEADER, ResumeSourceType.PROFILE, header))
    if candidate.summary:
        selected.append(
            _selection(
                candidate,
                ResumeSection.SUMMARY,
                ResumeSourceType.PROFILE,
                candidate.summary,
            )
        )

    work = _prioritized(candidate.work_experiences, relevant)[:4]
    for work_item in work:
        dates = _date_range(work_item.start_date, work_item.end_date)
        text = " | ".join(
            value
            for value in (work_item.title, work_item.employer, dates, work_item.description)
            if value
        )
        selected.append(
            ResumeSelection(
                uuid4(),
                ResumeSection.EXPERIENCE,
                ResumeSourceType.WORK_EXPERIENCE,
                work_item.id,
                work_item.evidence_source_id,
                text,
            )
        )

    for education_item in _prioritized(candidate.education, relevant)[:2]:
        text = " | ".join(
            value
            for value in (
                education_item.qualification,
                education_item.field_of_study,
                education_item.institution,
            )
            if value
        )
        selected.append(
            ResumeSelection(
                uuid4(),
                ResumeSection.EDUCATION,
                ResumeSourceType.EDUCATION,
                education_item.id,
                education_item.evidence_source_id,
                text,
            )
        )

    for project_item in _prioritized(candidate.projects, relevant)[:3]:
        text = " | ".join(
            value
            for value in (project_item.name, project_item.description, project_item.url)
            if value
        )
        selected.append(
            ResumeSelection(
                uuid4(),
                ResumeSection.PROJECTS,
                ResumeSourceType.PROJECT,
                project_item.id,
                project_item.evidence_source_id,
                text,
            )
        )

    for competency_item in _prioritized(candidate.competencies, relevant)[:12]:
        experience = (
            None
            if competency_item.months_experience is None
            else f"{competency_item.months_experience} months"
        )
        text = " | ".join(value for value in (competency_item.name, experience) if value)
        selected.append(
            ResumeSelection(
                uuid4(),
                ResumeSection.SKILLS,
                ResumeSourceType.COMPETENCY,
                competency_item.id,
                competency_item.evidence_source_id,
                text,
            )
        )

    selected.extend(
        ResumeSelection(
            uuid4(),
            ResumeSection.LANGUAGES,
            ResumeSourceType.LANGUAGE,
            item.id,
            item.evidence_source_id,
            f"{item.language} | {item.level.value}",
        )
        for item in _prioritized(candidate.languages, relevant)
    )
    return tuple(selected)


def _selection(
    candidate: CandidateProfile,
    section: ResumeSection,
    source_type: ResumeSourceType,
    text: str,
) -> ResumeSelection:
    return ResumeSelection(
        uuid4(), section, source_type, candidate.id, candidate.evidence_source_id, text
    )


def _prioritized[T: WorkExperience | Education | Project | Competency | LanguageProficiency](
    items: tuple[T, ...], relevant: set[UUID]
) -> tuple[T, ...]:
    return tuple(sorted(items, key=lambda item: (item.id not in relevant, str(item.id))))


def _date_range(start: date | None, end: date | None) -> str | None:
    if start is None and end is None:
        return None
    return f"{start.isoformat() if start else '?'} - {end.isoformat() if end else 'present'}"
