"""Typed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JOBHUNTER_",
        extra="ignore",
    )

    app_name: str = "JobHunter AI"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://jobhunter:jobhunter@127.0.0.1:5432/jobhunter"
    )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable configuration object."""

    return Settings()
