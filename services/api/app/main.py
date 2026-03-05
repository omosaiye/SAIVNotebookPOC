from __future__ import annotations

from fastapi import FastAPI

from services.api.app.auth.router import router as auth_router
from services.api.app.files.router import router as files_router
from services.api.app.upload_and_ask.router import router as upload_and_ask_router
from services.shared.config import load_api_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Private LLM API", version="0.1.0")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        settings = load_api_settings()
        return {
            "status": "ok",
            "service": settings.service_name,
            "environment": settings.app_env,
        }

    app.include_router(auth_router)
    app.include_router(files_router)
    app.include_router(upload_and_ask_router)

    return app


app = create_app()
