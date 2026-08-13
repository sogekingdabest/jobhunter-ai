"""Tests for typed application configuration."""

import pytest
from pydantic import ValidationError

from jobhunter.config import Settings

MAX_EXTRACTED_CHARACTERS = 100_000
MAX_REDIRECTS = 5
TOTAL_TIMEOUT_SECONDS = 20


def test_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOBHUNTER_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.app_name == "JobHunter AI"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert str(settings.database_url) == (
        "postgresql+psycopg://jobhunter:jobhunter@127.0.0.1:5432/jobhunter"
    )
    assert str(settings.document_storage_path).replace("\\", "/") == "storage/documents"
    assert settings.document_max_size_bytes == 10 * 1024 * 1024
    assert settings.job_url_max_response_bytes == 2 * 1024 * 1024
    assert settings.job_url_max_extracted_characters == MAX_EXTRACTED_CHARACTERS
    assert settings.job_url_max_redirects == MAX_REDIRECTS
    assert settings.job_url_total_timeout_seconds == TOTAL_TIMEOUT_SECONDS


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="staging", _env_file=None)


def test_settings_reject_non_postgres_database() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///jobhunter.db", _env_file=None)


def test_settings_reject_non_positive_document_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(document_max_size_bytes=0, _env_file=None)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("job_url_max_response_bytes", 0),
        ("job_url_max_extracted_characters", 0),
        ("job_url_max_redirects", 11),
        ("job_url_connect_timeout_seconds", 0),
        ("job_url_read_timeout_seconds", 0),
        ("job_url_total_timeout_seconds", 0),
    ],
)
def test_settings_reject_unsafe_job_url_limits(name: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**{name: value}, _env_file=None)  # type: ignore[arg-type]
