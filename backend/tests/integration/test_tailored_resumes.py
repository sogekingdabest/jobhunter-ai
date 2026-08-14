"""End-to-end PostgreSQL tests for tailored resume provenance and review."""

import asyncio
from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from jobhunter.config import Settings
from jobhunter.infrastructure.database.session import Database
from jobhunter.main import create_app
from jobhunter.resume.domain.models import ResumeStatus
from jobhunter.resume.infrastructure.database.repository import (
    SqlAlchemyTailoredResumeRepository,
)
from jobhunter.resume.ports.repository import TailoredResumeRepositoryConflictError
from tests.integration.test_candidate_profiles import (
    get_test_database_url,
    migrate,
)
from tests.integration.test_candidate_profiles import payload as candidate_payload
from tests.integration.test_job_offers import payload as job_payload

pytestmark = pytest.mark.integration


def test_tailored_resume_api_preserves_provenance_and_review() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))

    with TestClient(app) as client:
        candidate = client.post("/candidate-profiles", json=candidate_payload()).json()
        offer = client.post("/job-offers/manual", json=job_payload()).json()
        assessment = client.post(
            "/match-assessments",
            json={"candidate_profile_id": candidate["id"], "job_offer_id": offer["id"]},
        ).json()
        response = client.post(
            "/tailored-resumes",
            json={
                "candidate_profile_id": candidate["id"],
                "job_offer_id": offer["id"],
                "match_assessment_id": assessment["id"],
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        resume = response.json()
        assert resume["generation_version"] == "tailored-resume-v1"
        assert resume["status"] == "needs_review"
        assert resume["provider"] is None
        assert resume["fragments"]
        assert all(fragment["sources"] for fragment in resume["fragments"])
        assert all(
            fragment["generated_text"] == fragment["sources"][0]["source_text"]
            for fragment in resume["fragments"]
        )

        fetched = client.get(f"/tailored-resumes/{resume['id']}")
        assert fetched.json() == resume
        reviewed = client.patch(
            f"/tailored-resumes/{resume['id']}/review", json={"decision": "approved"}
        )
        assert reviewed.status_code == status.HTTP_200_OK
        assert reviewed.json()["status"] == "approved"
        assert reviewed.json()["revision"] == 1
        assert (
            client.patch(
                f"/tailored-resumes/{resume['id']}/review", json={"decision": "rejected"}
            ).status_code
            == status.HTTP_409_CONFLICT
        )

        assert (
            client.post(
                "/tailored-resumes",
                json={
                    "candidate_profile_id": candidate["id"],
                    "job_offer_id": offer["id"],
                    "match_assessment_id": assessment["id"],
                    "use_llm": True,
                },
            ).status_code
            == status.HTTP_503_SERVICE_UNAVAILABLE
        )
        assert (
            client.delete(f"/candidate-profiles/{candidate['id']}").status_code
            == status.HTTP_204_NO_CONTENT
        )
        assert (
            client.get(f"/tailored-resumes/{resume['id']}").status_code == status.HTTP_404_NOT_FOUND
        )


def test_tailored_resume_repository_detects_stale_review() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))

    with TestClient(app) as client:
        candidate = client.post("/candidate-profiles", json=candidate_payload()).json()
        offer = client.post("/job-offers/manual", json=job_payload()).json()
        assessment = client.post(
            "/match-assessments",
            json={"candidate_profile_id": candidate["id"], "job_offer_id": offer["id"]},
        ).json()
        resume = client.post(
            "/tailored-resumes",
            json={
                "candidate_profile_id": candidate["id"],
                "job_offer_id": offer["id"],
                "match_assessment_id": assessment["id"],
            },
        ).json()

    asyncio.run(_exercise_repository_conflict(database_url, UUID(resume["id"])))


async def _exercise_repository_conflict(database_url: str, resume_id: UUID) -> None:
    database = Database(database_url)
    try:
        async with database.session() as session:
            repository = SqlAlchemyTailoredResumeRepository(session)
            original = await repository.get(resume_id)
            assert original is not None
            assert await repository.get(uuid4()) is None
            missing_id = uuid4()
            missing = replace(
                original,
                id=missing_id,
                fragments=tuple(
                    replace(fragment, resume_id=missing_id) for fragment in original.fragments
                ),
            )
            assert await repository.replace(missing) is None

            approved = original.review(ResumeStatus.APPROVED, reviewed_at=original.created_at)
            assert await repository.replace(approved) == approved
            rejected = original.review(ResumeStatus.REJECTED, reviewed_at=original.created_at)
            with pytest.raises(TailoredResumeRepositoryConflictError):
                await repository.replace(rejected)
    finally:
        await database.dispose()
