from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import health, materials, questions
from server.answers.library_chat import LibraryChatAnswerComposer, create_library_chat_answer_composer_from_config
from server.core.config import ALLOWED_ORIGINS, EMBEDDING_AUTO_GENERATE, RETRIEVAL_BACKEND
from server.materials.observation import MaterialUploadObservationSink, NoopMaterialUploadObservationSink
from server.materials.store import MaterialStore
from server.questions.observation import NoopQuestionObservationSink, QuestionObservationSink
from server.retrieval.search import RAG_SIMILARITY_THRESHOLD, RAG_TOP_K
from server.retrieval.embeddings import create_ollama_embedding_provider_from_config
from server.retrieval.supabase import create_supabase_retrieval_repository_from_config
from server.runtime.config_snapshot import RuntimeConfigSettings


def create_app(
    store: MaterialStore | None = None,
    *,
    embedding_auto_generate: bool | None = None,
    retrieval_backend: str | None = None,
    retrieval_top_k: int | None = None,
    retrieval_similarity_threshold: float | None = None,
    library_chat_answer_composer: LibraryChatAnswerComposer | None = None,
    fact_proposer_backend: str | None = None,
    material_upload_observation_sink: MaterialUploadObservationSink | None = None,
    question_observation_sink: QuestionObservationSink | None = None,
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
            retrieval_backend=active_retrieval_backend,
        )
    app.state.runtime_config_settings = RuntimeConfigSettings(
        retrieval_backend=app.state.material_store.retrieval_backend,
        retrieval_top_k=RAG_TOP_K if retrieval_top_k is None else retrieval_top_k,
        retrieval_similarity_threshold=(
            RAG_SIMILARITY_THRESHOLD
            if retrieval_similarity_threshold is None
            else retrieval_similarity_threshold
        ),
        embedding_auto_generate=app.state.material_store.embedding_auto_generate,
        embedding_profile=app.state.material_store.embedding_profile,
    )
    app.state.library_chat_answer_composer = (
        library_chat_answer_composer
        or create_library_chat_answer_composer_from_config(backend=fact_proposer_backend)
    )
    app.state.material_upload_observation_sink = (
        material_upload_observation_sink or NoopMaterialUploadObservationSink()
    )
    app.state.question_observation_sink = question_observation_sink or NoopQuestionObservationSink()

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
