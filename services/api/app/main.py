from __future__ import annotations

from fastapi import FastAPI

from services.shared.config import load_api_settings


def create_app() -> FastAPI:
    settings = load_api_settings()

    app = FastAPI(title="Private LLM API", version="0.1.0")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.service_name,
            "environment": settings.app_env,
        }

    return app


app = create_app()
