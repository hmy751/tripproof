from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import health, materials, questions
from server.core.config import ALLOWED_ORIGINS
from server.materials.store import MaterialStore


def create_app(store: MaterialStore | None = None) -> FastAPI:
    app = FastAPI(title="TripProof Backend")
    app.state.material_store = store or MaterialStore()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(materials.router)
    app.include_router(questions.router)

    return app


app = create_app()
