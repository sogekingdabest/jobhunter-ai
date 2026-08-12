"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from jobhunter import __version__
from jobhunter.api.router import api_router
from jobhunter.config import Settings, get_settings
from jobhunter.infrastructure.database.session import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    resolved_settings = settings or get_settings()
    database = Database(str(resolved_settings.database_url))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await database.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=__version__,
        description="Explainable and provenance-aware job matching API.",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database = database
    application.include_router(api_router)
    return application


app = create_app()
