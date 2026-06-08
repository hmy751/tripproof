from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

from server.core.config import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OLLAMA_BASE_URL,
)
from server.retrieval.models import EmbeddingRecord, SourceUnit


class EmbeddingProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingProfile:
    provider: str
    model: str
    dimensions: int


class EmbeddingProvider(Protocol):
    profile: EmbeddingProfile

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class OllamaEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        dimensions: int,
        timeout_seconds: float = 6.0,
        document_prefix: str = "search_document: ",
        query_prefix: str = "search_query: ",
    ) -> None:
        self.profile = EmbeddingProfile(provider="ollama", model=model, dimensions=dimensions)
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._document_prefix = document_prefix
        self._query_prefix = query_prefix

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed([self._document_prefix + text for text in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self._query_prefix + text])[0]

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.profile.model, "input": inputs}).encode("utf-8")
        http_request = request.Request(
            f"{self._base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                raw = response.read()
        except error.URLError as exc:
            raise EmbeddingProviderError(f"Ollama embedding request failed: {exc}") from exc

        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise EmbeddingProviderError("Ollama embedding response was not valid JSON.") from exc

        embeddings = body.get("embeddings")
        if not isinstance(embeddings, list):
            raise EmbeddingProviderError("Ollama embedding response did not include embeddings.")

        vectors: list[list[float]] = []
        for embedding in embeddings:
            if not isinstance(embedding, list):
                raise EmbeddingProviderError("Ollama embedding item was not a vector.")
            vector = [float(value) for value in embedding]
            if len(vector) != self.profile.dimensions:
                raise EmbeddingProviderError(
                    f"Expected embedding dimension {self.profile.dimensions}, got {len(vector)}."
                )
            vectors.append(vector)

        if len(vectors) != len(inputs):
            raise EmbeddingProviderError("Ollama returned a different number of embeddings than requested.")

        return vectors


def default_embedding_profile() -> EmbeddingProfile:
    return EmbeddingProfile(
        provider=EMBEDDING_PROVIDER,
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
    )


def create_ollama_embedding_provider_from_config() -> OllamaEmbeddingProvider:
    return OllamaEmbeddingProvider(
        base_url=OLLAMA_BASE_URL,
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
    )


def build_embedding_records(
    source_units: Iterable[SourceUnit],
    *,
    provider: EmbeddingProvider | None,
    profile: EmbeddingProfile | None = None,
    generate: bool = False,
) -> list[EmbeddingRecord]:
    units = list(source_units)
    active_profile = provider.profile if provider else profile or default_embedding_profile()

    if not units:
        return []

    if not generate or provider is None:
        return [_pending_record(unit, active_profile) for unit in units]

    try:
        vectors = provider.embed_documents([unit.text for unit in units])
    except EmbeddingProviderError as exc:
        return [_failed_record(unit, active_profile, str(exc)) for unit in units]

    return [
        EmbeddingRecord(
            id=_embedding_id(unit=unit, profile=active_profile),
            source_unit_id=unit.id,
            provider=active_profile.provider,
            model=active_profile.model,
            dimensions=active_profile.dimensions,
            vector=vector,
            status="ready",
        )
        for unit, vector in zip(units, vectors, strict=True)
    ]


def _pending_record(unit: SourceUnit, profile: EmbeddingProfile) -> EmbeddingRecord:
    return EmbeddingRecord(
        id=_embedding_id(unit=unit, profile=profile),
        source_unit_id=unit.id,
        provider=profile.provider,
        model=profile.model,
        dimensions=profile.dimensions,
        vector=None,
        status="pending",
    )


def _failed_record(unit: SourceUnit, profile: EmbeddingProfile, error_message: str) -> EmbeddingRecord:
    return EmbeddingRecord(
        id=_embedding_id(unit=unit, profile=profile),
        source_unit_id=unit.id,
        provider=profile.provider,
        model=profile.model,
        dimensions=profile.dimensions,
        vector=None,
        status="failed",
        error=error_message,
    )


def _embedding_id(*, unit: SourceUnit, profile: EmbeddingProfile) -> str:
    model_slug = profile.model.replace("/", "_").replace(":", "_").replace("-", "_")
    return f"emb_{unit.id}_{model_slug}"
