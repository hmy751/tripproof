from __future__ import annotations

import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from server.api.routes import health, materials, questions
from server.answers.library_chat import (
    LibraryChatAnswerComposer,
    create_library_chat_answer_composer_from_config,
)
from server.core.config import (
    ALLOWED_ORIGINS,
    CORS_EXPOSE_HEADERS,
    EMBEDDING_AUTO_GENERATE,
    LANGSMITH_API_KEY,
    LANGSMITH_OBSERVATION_ENABLED,
    LANGSMITH_PROJECT,
    OBSERVATION_EXPORT_DIR,
)
from server.materials.observation import MaterialUploadObservationSink
from server.materials.store import MaterialStore
from server.observations.export import (
    FanoutObservationExporter,
    LocalArtifactObservationExporter,
    MaterialUploadObservationExportSink,
    NoopObservationExporter,
    ObservationRequestContext,
    ObservationExporter,
    QuestionObservationExportSink,
    new_observation_request_context,
    reset_current_observation_request_context,
    set_current_observation_request_context,
)
from server.observations.langsmith import (
    LangSmithObservationExporter,
    LangSmithRunTreeWriter,
)
from server.questions.observation import QuestionObservationSink
from server.retrieval.search import RAG_SIMILARITY_THRESHOLD, RAG_TOP_K
from server.retrieval.embeddings import create_ollama_embedding_provider_from_config
from server.retrieval.repository import RetrievalRepository
from server.retrieval.supabase import create_supabase_retrieval_repository_from_config
from server.runtime.config_snapshot import RuntimeConfigSettings

REQUEST_ID_HEADER = "X-TripProof-Request-Id"
CORRELATION_ID_HEADER = "X-TripProof-Correlation-Id"
_CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def create_app(
    store: MaterialStore | None = None,
    *,
    embedding_auto_generate: bool | None = None,
    retrieval_repository: RetrievalRepository | None = None,
    retrieval_top_k: int | None = None,
    retrieval_similarity_threshold: float | None = None,
    library_chat_answer_composer: LibraryChatAnswerComposer | None = None,
    material_upload_observation_sink: MaterialUploadObservationSink | None = None,
    question_observation_sink: QuestionObservationSink | None = None,
    observation_exporter: ObservationExporter | None = None,
) -> FastAPI:
    app = FastAPI(title="TripProof Backend")
    if store is not None:
        app.state.material_store = store
    else:
        active_embedding_auto_generate = (
            EMBEDDING_AUTO_GENERATE
            if embedding_auto_generate is None
            else embedding_auto_generate
        )
        embedding_provider = (
            create_ollama_embedding_provider_from_config()
            if active_embedding_auto_generate
            else None
        )
        if retrieval_repository is not None:
            active_retrieval_repository = retrieval_repository
            active_retrieval_backend = "memory"
        else:
            active_retrieval_repository = (
                create_supabase_retrieval_repository_from_config()
            )
            active_retrieval_backend = "supabase"
        app.state.material_store = MaterialStore(
            embedding_provider=embedding_provider,
            embedding_auto_generate=active_embedding_auto_generate,
            retrieval_repository=active_retrieval_repository,
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
        or create_library_chat_answer_composer_from_config()
    )
    active_observation_exporter = (
        observation_exporter or _create_default_observation_exporter()
    )
    app.state.observation_exporter = active_observation_exporter
    app.state.material_upload_observation_sink = (
        material_upload_observation_sink
        or MaterialUploadObservationExportSink(active_observation_exporter)
    )
    app.state.question_observation_sink = (
        question_observation_sink
        or QuestionObservationExportSink(active_observation_exporter)
    )

    @app.middleware("http")
    async def attach_request_context(request: Request, call_next) -> Response:
        context = _observation_request_context_from_headers(request.headers)
        request.state.tripproof_observation_request_context = context
        token = set_current_observation_request_context(context)
        try:
            response = await call_next(request)
        finally:
            reset_current_observation_request_context(token)
        response.headers[REQUEST_ID_HEADER] = context.request_id
        response.headers[CORRELATION_ID_HEADER] = context.correlation_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=CORS_EXPOSE_HEADERS,
    )

    app.include_router(health.router)
    app.include_router(materials.router)
    app.include_router(questions.router)

    return app


def _create_default_observation_exporter() -> ObservationExporter:
    exporters: list[ObservationExporter] = []

    if OBSERVATION_EXPORT_DIR.strip():
        exporters.append(LocalArtifactObservationExporter(OBSERVATION_EXPORT_DIR))

    if LANGSMITH_OBSERVATION_ENABLED and LANGSMITH_API_KEY:
        exporters.append(
            LangSmithObservationExporter(
                LangSmithRunTreeWriter(project_name=LANGSMITH_PROJECT or None)
            )
        )

    if not exporters:
        return NoopObservationExporter()
    if len(exporters) == 1:
        return exporters[0]
    return FanoutObservationExporter(exporters)


def _observation_request_context_from_headers(headers) -> ObservationRequestContext:
    header_value = headers.get(CORRELATION_ID_HEADER)
    correlation_id = _valid_correlation_id(header_value)
    if correlation_id is None:
        return new_observation_request_context()
    return new_observation_request_context(
        correlation_id=correlation_id,
        correlation_id_source="header",
    )


def _valid_correlation_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not _CORRELATION_ID_RE.fullmatch(trimmed):
        return None
    return trimmed


app = create_app()
