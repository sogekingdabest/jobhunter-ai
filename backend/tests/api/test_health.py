"""Tests for the API health endpoint."""

from fastapi.testclient import TestClient
from starlette import status

from jobhunter.config import Settings
from jobhunter.main import create_app


def test_health_returns_service_metadata() -> None:
    app = create_app(
        Settings(
            app_name="JobHunter AI Test",
            environment="test",
            _env_file=None,
        )
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "service": "JobHunter AI Test",
        "environment": "test",
        "version": "0.1.0",
    }


def test_openapi_exposes_health_operation() -> None:
    app = create_app(Settings(environment="test", _env_file=None))

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
