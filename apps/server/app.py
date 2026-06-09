from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import health, materials, questions
from server.core.config import ALLOWED_ORIGINS, EMBEDDING_AUTO_GENERATE, RETRIEVAL_BACKEND
from server.materials.store import MaterialStore
from server.retrieval.embeddings import create_ollama_embedding_provider_from_config
from server.retrieval.supabase import create_supabase_retrieval_repository_from_config


def create_app(
    store: MaterialStore | None = None,
    *,
    embedding_auto_generate: bool | None = None,
    retrieval_backend: str | None = None,
) -> FastAPI:
    app = FastAPI(title="TripProof Backend")
    if store is not None:
        app.state.material_store = store
    else:
        active_embedding_auto_generate = (
            EMBEDDING_AUTO_GENERATE if embedding_auto_generate is None else embedding_auto_generate
        )
        embedding_provider = create_ollama_embedding_provider_from_config() if active_embedding_auto_generate else None
        active_retrieval_backend = (retrieval_backend or RETRIEVAL_BACKEND).lower()
        retrieval_repository = (
            create_supabase_retrieval_repository_from_config()
            if active_retrieval_backend == "supabase"
            else None
        )
        app.state.material_store = MaterialStore(
            embedding_provider=embedding_provider,
            embedding_auto_generate=active_embedding_auto_generate,
            retrieval_repository=retrieval_repository,
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
