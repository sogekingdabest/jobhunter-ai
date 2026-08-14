"""SQLAlchemy persistence for traceable tailored resumes."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from jobhunter.resume.domain.models import (
    ResumeFragment,
    ResumeSource,
    TailoredResume,
)
from jobhunter.resume.infrastructure.database.models import (
    ResumeFragmentModel,
    ResumeSourceModel,
    TailoredResumeModel,
)
from jobhunter.resume.ports.repository import TailoredResumeRepositoryConflictError


class SqlAlchemyTailoredResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, resume: TailoredResume) -> TailoredResume:
        self._session.add(_to_model(resume))
        await self._session.commit()
        return await self._required(resume.id)

    async def get(self, resume_id: UUID) -> TailoredResume | None:
        model = await self._load(resume_id)
        return None if model is None else _to_domain(model)

    async def replace(self, resume: TailoredResume) -> TailoredResume | None:
        model = await self._load(resume.id, for_update=True)
        if model is None:
            return None
        if model.revision != resume.revision - 1:
            raise TailoredResumeRepositoryConflictError
        model.status = resume.status
        model.revision = resume.revision
        model.reviewed_at = resume.reviewed_at
        await self._session.commit()
        return await self._required(resume.id)

    async def _load(
        self, resume_id: UUID, *, for_update: bool = False
    ) -> TailoredResumeModel | None:
        statement = (
            select(TailoredResumeModel)
            .where(TailoredResumeModel.id == resume_id)
            .options(
                selectinload(TailoredResumeModel.fragments).selectinload(
                    ResumeFragmentModel.sources
                )
            )
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(TailoredResumeModel | None, await self._session.scalar(statement))

    async def _required(self, resume_id: UUID) -> TailoredResume:
        stored = await self.get(resume_id)
        if stored is None:  # pragma: no cover - protected by preceding transaction
            raise RuntimeError("tailored_resume_not_persisted")
        return stored


def _to_model(resume: TailoredResume) -> TailoredResumeModel:
    return TailoredResumeModel(
        id=resume.id,
        candidate_profile_id=resume.candidate_profile_id,
        job_offer_id=resume.job_offer_id,
        match_assessment_id=resume.match_assessment_id,
        generation_version=resume.generation_version,
        candidate_updated_at=resume.candidate_updated_at,
        job_content_fingerprint=resume.job_content_fingerprint,
        status=resume.status,
        revision=resume.revision,
        created_at=resume.created_at,
        reviewed_at=resume.reviewed_at,
        provider=resume.provider,
        model=resume.model,
        fragments=[
            ResumeFragmentModel(
                id=fragment.id,
                resume_id=resume.id,
                position=fragment.position,
                section=fragment.section,
                generated_text=fragment.generated_text,
                method=fragment.method,
                sources=[
                    ResumeSourceModel(
                        id=source.id,
                        fragment_id=fragment.id,
                        position=source_position,
                        source_type=source.source_type,
                        source_id=source.source_id,
                        evidence_source_id=source.evidence_source_id,
                        source_text=source.source_text,
                    )
                    for source_position, source in enumerate(fragment.sources)
                ],
            )
            for fragment in resume.fragments
        ],
    )


def _to_domain(model: TailoredResumeModel) -> TailoredResume:
    return TailoredResume(
        id=model.id,
        candidate_profile_id=model.candidate_profile_id,
        job_offer_id=model.job_offer_id,
        match_assessment_id=model.match_assessment_id,
        generation_version=model.generation_version,
        candidate_updated_at=model.candidate_updated_at,
        job_content_fingerprint=model.job_content_fingerprint,
        status=model.status,
        revision=model.revision,
        created_at=model.created_at,
        reviewed_at=model.reviewed_at,
        provider=model.provider,
        model=model.model,
        fragments=tuple(
            ResumeFragment(
                id=fragment.id,
                resume_id=model.id,
                section=fragment.section,
                position=fragment.position,
                generated_text=fragment.generated_text,
                method=fragment.method,
                sources=tuple(
                    ResumeSource(
                        id=source.id,
                        source_type=source.source_type,
                        source_id=source.source_id,
                        evidence_source_id=source.evidence_source_id,
                        source_text=source.source_text,
                    )
                    for source in fragment.sources
                ),
            )
            for fragment in model.fragments
        ),
    )
