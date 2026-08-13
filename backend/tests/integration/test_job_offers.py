"""End-to-end PostgreSQL API tests for manual job offers."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import status
from fastapi.testclient import TestClient

from jobhunter.config import Settings
from jobhunter.main import create_app
from tests.jobs.factories import JOB_TEXT, normalization_payload

pytestmark = pytest.mark.integration


def get_test_database_url() -> str:
    url = os.getenv("JOBHUNTER_TEST_DATABASE_URL")
    if url is None:
        pytest.skip("JOBHUNTER_TEST_DATABASE_URL is not configured")
    return url


def migrate(database_url: str) -> None:
    backend_root = Path(__file__).parents[2]
    configuration = Config(backend_root / "alembic.ini")
    configuration.attributes["database_url"] = database_url
    command.upgrade(configuration, "head")


def payload() -> dict[str, object]:
    return {
        "raw_text": f"{JOB_TEXT}\nImport reference: {uuid4()}",
        "normalization": normalization_payload(),
    }


def test_manual_job_offer_import_get_and_duplicate_response() -> None:
    database_url = get_test_database_url()
    migrate(database_url)
    app = create_app(Settings(environment="test", database_url=database_url, _env_file=None))
    request_payload = payload()

    with TestClient(app) as client:
        created_response = client.post("/job-offers/manual", json=request_payload)
        assert created_response.status_code == status.HTTP_201_CREATED
        created = created_response.json()
        assert created["title"] == "Backend Engineer"
        assert created["fields"][0]["evidence_quote"] == "Acme Labs"

        fetched = client.get(f"/job-offers/{created['id']}")
        assert fetched.status_code == status.HTTP_200_OK
        assert fetched.json() == created

        duplicate = client.post("/job-offers/manual", json=request_payload)
        assert duplicate.status_code == status.HTTP_409_CONFLICT
        assert duplicate.json()["detail"] == "duplicate_job_offer"

        missing = client.get("/job-offers/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == status.HTTP_404_NOT_FOUND
