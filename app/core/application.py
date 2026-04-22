from __future__ import annotations

from fastapi import FastAPI

from app.api.legacy import router as legacy_router
from app.api.router import api_router
from app.core.config import get_settings
from app.core.runtime import configure_event_loop_policy


def create_app() -> FastAPI:
    settings = get_settings()
    configure_event_loop_policy()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(legacy_router)

    return app

