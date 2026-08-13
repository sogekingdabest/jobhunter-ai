"""SQLAlchemy implementation of the candidate profile repository port."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.candidate.domain.competencies import Competency, LanguageProficiency
from jobhunter.candidate.domain.experience import Education, Project, WorkExperience
from jobhunter.candidate.domain.profile import CandidateProfile
from jobhunter.candidate.infrastructure.database.models import (
    CandidateProfileModel,
    CompetencyModel,
    EducationModel,
    LanguageProficiencyModel,
    ProjectModel,
    WorkExperienceModel,
)
from jobhunter.documents.domain.entities import EvidenceSourceType
from jobhunter.documents.infrastructure.database.models import EvidenceSourceModel


class SqlAlchemyCandidateProfileRepository:
    """Persist the full candidate aggregate transactionally."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, profile: CandidateProfile) -> CandidateProfile:
        self._session.add(
            EvidenceSourceModel(
                id=profile.evidence_source_id,
                source_type=EvidenceSourceType.USER_STATEMENT,
                source_document_id=None,
            )
        )
        await self._session.flush()
        self._session.add(_to_model(profile))
        await self._session.commit()
        return await self._required(profile.id)

    async def get(self, profile_id: UUID) -> CandidateProfile | None:
        model = await self._load(profile_id)
        return None if model is None else _to_domain(model)

    async def replace(self, profile: CandidateProfile) -> CandidateProfile | None:
        model = await self._load(profile.id)
        if model is None:
            return None
        self._session.add(
            EvidenceSourceModel(
                id=profile.evidence_source_id,
                source_type=EvidenceSourceType.USER_STATEMENT,
                source_document_id=None,
            )
        )
        await self._session.flush()
        _replace_model(model, profile)
        await self._session.commit()
        return await self._required(profile.id)

    async def delete(self, profile_id: UUID) -> bool:
        model = await self._load(profile_id)
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True

    async def _load(self, profile_id: UUID) -> CandidateProfileModel | None:
        statement = (
            select(CandidateProfileModel)
            .where(CandidateProfileModel.id == profile_id)
            .options(
                selectinload(CandidateProfileModel.work_experiences),
                selectinload(CandidateProfileModel.education),
                selectinload(CandidateProfileModel.projects),
                selectinload(CandidateProfileModel.competencies),
                selectinload(CandidateProfileModel.languages),
            )
        )
        return cast(CandidateProfileModel | None, await self._session.scalar(statement))

    async def _required(self, profile_id: UUID) -> CandidateProfile:
        stored = await self.get(profile_id)
        if stored is None:  # pragma: no cover - protected by the transaction above
            raise RuntimeError("candidate_profile_not_persisted")
        return stored


def _to_model(profile: CandidateProfile) -> CandidateProfileModel:
    model = CandidateProfileModel(id=profile.id)
    _replace_model(model, profile)
    return model


def _replace_model(model: CandidateProfileModel, profile: CandidateProfile) -> None:
    model.evidence_source_id = profile.evidence_source_id
    model.full_name = profile.full_name
    model.headline = profile.headline
    model.summary = profile.summary
    model.email = profile.email
    model.phone = profile.phone
    model.location = profile.location
    model.remote_preference = profile.remote_preference
    model.preferred_roles = list(profile.preferred_roles)
    model.preferred_locations = list(profile.preferred_locations)
    model.work_experiences = [
        WorkExperienceModel(
            id=item.id,
            candidate_profile_id=profile.id,
            evidence_source_id=item.evidence_source_id,
            employer=item.employer,
            title=item.title,
            start_date=item.start_date,
            end_date=item.end_date,
            description=item.description,
        )
        for item in profile.work_experiences
    ]
    model.education = [
        EducationModel(
            id=item.id,
            candidate_profile_id=profile.id,
            evidence_source_id=item.evidence_source_id,
            institution=item.institution,
            qualification=item.qualification,
            field_of_study=item.field_of_study,
            start_date=item.start_date,
            end_date=item.end_date,
        )
        for item in profile.education
    ]
    model.projects = [
        ProjectModel(
            id=item.id,
            candidate_profile_id=profile.id,
            evidence_source_id=item.evidence_source_id,
            name=item.name,
            description=item.description,
            url=item.url,
        )
        for item in profile.projects
    ]
    model.competencies = [
        CompetencyModel(
            id=item.id,
            candidate_profile_id=profile.id,
            evidence_source_id=item.evidence_source_id,
            name=item.name,
            category=item.category,
            months_experience=item.months_experience,
        )
        for item in profile.competencies
    ]
    model.languages = [
        LanguageProficiencyModel(
            id=item.id,
            candidate_profile_id=profile.id,
            evidence_source_id=item.evidence_source_id,
            language=item.language,
            level=item.level,
        )
        for item in profile.languages
    ]


def _to_domain(model: CandidateProfileModel) -> CandidateProfile:
    return CandidateProfile(
        id=model.id,
        evidence_source_id=model.evidence_source_id,
        full_name=model.full_name,
        headline=model.headline,
        summary=model.summary,
        email=model.email,
        phone=model.phone,
        location=model.location,
        remote_preference=model.remote_preference,
        preferred_roles=tuple(model.preferred_roles),
        preferred_locations=tuple(model.preferred_locations),
        work_experiences=tuple(
            WorkExperience(
                id=item.id,
                evidence_source_id=item.evidence_source_id,
                employer=item.employer,
                title=item.title,
                start_date=item.start_date,
                end_date=item.end_date,
                description=item.description,
            )
            for item in sorted(model.work_experiences, key=lambda value: str(value.id))
        ),
        education=tuple(
            Education(
                id=item.id,
                evidence_source_id=item.evidence_source_id,
                institution=item.institution,
                qualification=item.qualification,
                field_of_study=item.field_of_study,
                start_date=item.start_date,
                end_date=item.end_date,
            )
            for item in sorted(model.education, key=lambda value: str(value.id))
        ),
        projects=tuple(
            Project(
                id=item.id,
                evidence_source_id=item.evidence_source_id,
                name=item.name,
                description=item.description,
                url=item.url,
            )
            for item in sorted(model.projects, key=lambda value: str(value.id))
        ),
        competencies=tuple(
            Competency(
                id=item.id,
                evidence_source_id=item.evidence_source_id,
                name=item.name,
                category=item.category,
                months_experience=item.months_experience,
            )
            for item in sorted(model.competencies, key=lambda value: str(value.id))
        ),
        languages=tuple(
            LanguageProficiency(
                id=item.id,
                evidence_source_id=item.evidence_source_id,
                language=item.language,
                level=item.level,
            )
            for item in sorted(model.languages, key=lambda value: str(value.id))
        ),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
