from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import health, materials, questions
from server.core.config import ALLOWED_ORIGINS, EMBEDDING_AUTO_GENERATE
from server.materials.store import MaterialStore
from server.retrieval.embeddings import create_ollama_embedding_provider_from_config


def create_app(store: MaterialStore | None = None) -> FastAPI:
    app = FastAPI(title="TripProof Backend")
    embedding_provider = create_ollama_embedding_provider_from_config() if EMBEDDING_AUTO_GENERATE else None
    app.state.material_store = store or MaterialStore(
        embedding_provider=embedding_provider,
        embedding_auto_generate=EMBEDDING_AUTO_GENERATE,
    )

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
