from __future__ import annotations

from dataclasses import dataclass

from server.retrieval.embeddings import EmbeddingProfile


@dataclass(frozen=True)
class RuntimeConfigSettings:
    retrieval_backend: str
    retrieval_top_k: int
    retrieval_similarity_threshold: float
    embedding_auto_generate: bool
    embedding_profile: EmbeddingProfile


@dataclass(frozen=True)
class RetrievalRuntimeConfigSnapshot:
    backend: str
    top_k: int
    similarity_threshold: float


@dataclass(frozen=True)
class EmbeddingRuntimeConfigSnapshot:
    auto_generate: bool
    provider: str
    model: str
    dimensions: int


@dataclass(frozen=True)
class PromptRuntimeConfigSnapshot:
    domain: str
    name: str
    version: str
    body_hash: str
    file_hash: str
    asset_path: str


@dataclass(frozen=True)
class AnswerModelRuntimeConfigSnapshot:
    backend: str
    model: str | None
    seed: int | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class RuntimeConfigSnapshot:
    retrieval: RetrievalRuntimeConfigSnapshot
    embedding: EmbeddingRuntimeConfigSnapshot
    prompt: PromptRuntimeConfigSnapshot | None = None
    answer_model: AnswerModelRuntimeConfigSnapshot | None = None


def runtime_config_snapshot_from_settings(
    settings: RuntimeConfigSettings,
    *,
    prompt: PromptRuntimeConfigSnapshot | None = None,
    answer_model: AnswerModelRuntimeConfigSnapshot | None = None,
) -> RuntimeConfigSnapshot:
    return RuntimeConfigSnapshot(
        retrieval=RetrievalRuntimeConfigSnapshot(
            backend=settings.retrieval_backend,
            top_k=settings.retrieval_top_k,
            similarity_threshold=settings.retrieval_similarity_threshold,
        ),
        embedding=EmbeddingRuntimeConfigSnapshot(
            auto_generate=settings.embedding_auto_generate,
            provider=settings.embedding_profile.provider,
            model=settings.embedding_profile.model,
            dimensions=settings.embedding_profile.dimensions,
        ),
        prompt=prompt,
        answer_model=answer_model,
    )


def prompt_runtime_config_snapshot_from_composer(
    answer_composer: object,
) -> PromptRuntimeConfigSnapshot | None:
    try:
        prompt = getattr(answer_composer, "prompt", None)
        snapshot = (
            prompt.snapshot()
            if prompt is not None and hasattr(prompt, "snapshot")
            else None
        )
    except Exception:
        return None

    if not isinstance(snapshot, dict):
        return None

    domain = _string_snapshot_value(snapshot, "domain")
    name = _string_snapshot_value(snapshot, "name")
    version = _string_snapshot_value(snapshot, "version")
    body_hash = _string_snapshot_value(snapshot, "bodyHash")
    file_hash = _string_snapshot_value(snapshot, "fileHash")
    asset_path = _string_snapshot_value(snapshot, "assetPath")
    if None in (domain, name, version, body_hash, file_hash, asset_path):
        return None

    return PromptRuntimeConfigSnapshot(
        domain=domain,
        name=name,
        version=version,
        body_hash=body_hash,
        file_hash=file_hash,
        asset_path=asset_path,
    )


def answer_model_runtime_config_snapshot_from_composer(
    answer_composer: object,
) -> AnswerModelRuntimeConfigSnapshot | None:
    snapshot_method = getattr(answer_composer, "runtime_answer_model_snapshot", None)
    if not callable(snapshot_method):
        return None

    try:
        snapshot = snapshot_method()
    except Exception:
        return None

    if not isinstance(snapshot, dict):
        return None

    backend = _string_snapshot_value(snapshot, "backend")
    if backend is None:
        return None

    return AnswerModelRuntimeConfigSnapshot(
        backend=backend,
        model=_string_snapshot_value(snapshot, "model"),
        seed=_int_snapshot_value(snapshot, "seed"),
        temperature=_float_snapshot_value(snapshot, "temperature"),
    )


def _string_snapshot_value(snapshot: dict[object, object], key: str) -> str | None:
    value = snapshot.get(key)
    return value if isinstance(value, str) else None


def _int_snapshot_value(snapshot: dict[object, object], key: str) -> int | None:
    value = snapshot.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _float_snapshot_value(snapshot: dict[object, object], key: str) -> float | None:
    value = snapshot.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
