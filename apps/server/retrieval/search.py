from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import sqrt
from typing import Literal

from server.core.config import RAG_SIMILARITY_THRESHOLD, RAG_TOP_K
from server.retrieval.chunking import chunk_text
from server.retrieval.embeddings import EmbeddingProvider, EmbeddingProviderError
from server.retrieval.models import (
    AnswerContext,
    EmbeddingRecord,
    RetrievedSource,
    SourceUnit,
)
from server.retrieval.repository import RetrievalRepository


@dataclass(frozen=True)
class SourceUnitMatch:
    source_unit: SourceUnit
    score: float
    lexical_score: int
    vector_score: float | None


@dataclass(frozen=True)
class SourceUnitExcerpt:
    source_unit: SourceUnit
    excerpt: str
    score: float
    lexical_score: int
    vector_score: float | None


SourceRetrievalStrategy = Literal[
    "repository_vector", "local_vector", "lexical", "none"
]


@dataclass(frozen=True)
class SourceRetrievalTrace:
    strategy: SourceRetrievalStrategy
    query_embedding_attempted: bool
    query_embedding_available: bool
    vector_attempted: bool
    vector_candidate_count: int
    fallback_used: bool


@dataclass(frozen=True)
class RetrievedContext:
    context: AnswerContext
    source_retrieval: SourceRetrievalTrace


@dataclass(frozen=True)
class QueryEmbeddingAttempt:
    attempted: bool
    vector: list[float] | None

    @property
    def available(self) -> bool:
        return self.vector is not None


def select_excerpt(
    texts: Iterable[str], query: str, *, max_chars: int = 420
) -> str | None:
    normalized = _collapse_whitespace("\n\n".join(texts))
    if not normalized:
        return None

    terms = _query_terms(query)
    chunks = chunk_text(normalized, chunk_size=max(max_chars, 800), overlap=120)
    if not chunks:
        return None

    best_chunk = max(chunks, key=lambda chunk: _score_text(chunk.text, terms))
    excerpt = best_chunk.text[:max_chars].strip()
    return excerpt or None


def select_source_unit(
    *,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    query: str,
    embedding_provider: EmbeddingProvider | None = None,
) -> SourceUnitMatch | None:
    matches = _rank_source_units(
        source_units=source_units,
        embedding_records=embedding_records,
        query=query,
        embedding_provider=embedding_provider,
    )
    return matches[0] if matches else None


def retrieve_context(
    *,
    target_id: str,
    query: str,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None = None,
    retrieval_repository: RetrievalRepository | None = None,
    material_ids: Iterable[str] | None = None,
    top_k: int = RAG_TOP_K,
    similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> AnswerContext:
    return retrieve_context_with_trace(
        target_id=target_id,
        query=query,
        source_units=source_units,
        embedding_records=embedding_records,
        embedding_provider=embedding_provider,
        retrieval_repository=retrieval_repository,
        material_ids=material_ids,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    ).context


def retrieve_context_with_trace(
    *,
    target_id: str,
    query: str,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None = None,
    retrieval_repository: RetrievalRepository | None = None,
    material_ids: Iterable[str] | None = None,
    top_k: int = RAG_TOP_K,
    similarity_threshold: float = RAG_SIMILARITY_THRESHOLD,
) -> RetrievedContext:
    units = list(source_units)
    records = list(embedding_records)
    material_id_list = list(material_ids) if material_ids is not None else None
    query_embedding = _resolve_query_embedding(
        query=query,
        embedding_records=records,
        embedding_provider=embedding_provider,
    )
    repository_vector_attempted = _can_attempt_repository_vector(
        query_embedding=query_embedding,
        retrieval_repository=retrieval_repository,
        material_ids=material_id_list,
    )

    if repository_vector_attempted:
        repository_context = _retrieve_repository_vector_context(
            target_id=target_id,
            query=query,
            query_embedding=query_embedding,
            retrieval_repository=retrieval_repository,
            material_ids=material_id_list,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        if repository_context is not None:
            return repository_context

    return _retrieve_ranked_context(
        target_id=target_id,
        query=query,
        source_units=units,
        embedding_records=records,
        embedding_provider=embedding_provider,
        query_embedding=query_embedding,
        repository_vector_attempted=repository_vector_attempted,
        top_k=top_k,
    )


def _resolve_query_embedding(
    *,
    query: str,
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None,
) -> QueryEmbeddingAttempt:
    records = list(embedding_records)
    attempted = _can_attempt_query_vector(
        embedding_records=records,
        embedding_provider=embedding_provider,
    )
    vector = _query_vector(
        query=query,
        embedding_records=records,
        embedding_provider=embedding_provider,
    )
    return QueryEmbeddingAttempt(attempted=attempted, vector=vector)


def _can_attempt_repository_vector(
    *,
    query_embedding: QueryEmbeddingAttempt,
    retrieval_repository: RetrievalRepository | None,
    material_ids: list[str] | None,
) -> bool:
    return (
        query_embedding.available
        and retrieval_repository is not None
        and material_ids is not None
    )


def _retrieve_repository_vector_context(
    *,
    target_id: str,
    query: str,
    query_embedding: QueryEmbeddingAttempt,
    retrieval_repository: RetrievalRepository | None,
    material_ids: list[str] | None,
    top_k: int,
    similarity_threshold: float,
) -> RetrievedContext | None:
    if (
        query_embedding.vector is None
        or retrieval_repository is None
        or material_ids is None
    ):
        return None

    vector_matches = retrieval_repository.match_source_units(
        material_ids=material_ids,
        query_embedding=query_embedding.vector,
        limit=top_k,
        similarity_threshold=similarity_threshold,
    )
    if not vector_matches:
        return None

    terms = _query_terms(query)
    candidates = [
        RetrievedSource(
            target_id=target_id,
            query=query,
            source_unit=match.source_unit,
            score=match.similarity,
            lexical_score=_score_text(match.source_unit.search_text, terms),
            vector_score=match.similarity,
        )
        for match in vector_matches
    ]
    return RetrievedContext(
        context=AnswerContext(target_id=target_id, query=query, candidates=candidates),
        source_retrieval=SourceRetrievalTrace(
            strategy="repository_vector",
            query_embedding_attempted=query_embedding.attempted,
            query_embedding_available=query_embedding.available,
            vector_attempted=True,
            vector_candidate_count=len(vector_matches),
            fallback_used=False,
        ),
    )


def _retrieve_ranked_context(
    *,
    target_id: str,
    query: str,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None,
    query_embedding: QueryEmbeddingAttempt,
    repository_vector_attempted: bool,
    top_k: int,
) -> RetrievedContext:
    records = list(embedding_records)
    matches = _rank_source_units(
        source_units=source_units,
        embedding_records=records,
        query=query,
        embedding_provider=embedding_provider,
        query_vector=query_embedding.vector,
        resolve_query_vector=False,
    )
    candidates = [
        RetrievedSource(
            target_id=target_id,
            query=query,
            source_unit=match.source_unit,
            score=match.score,
            lexical_score=match.lexical_score,
            vector_score=match.vector_score,
        )
        for match in matches[:top_k]
        if match.score > 0
    ]
    vector_candidate_count = sum(
        candidate.vector_score is not None for candidate in candidates
    )
    strategy = _ranked_retrieval_strategy(
        candidates=candidates,
        vector_candidate_count=vector_candidate_count,
    )
    local_vector_attempted = _can_use_local_vectors(
        query_embedding=query_embedding,
        embedding_records=records,
    )
    return RetrievedContext(
        context=AnswerContext(target_id=target_id, query=query, candidates=candidates),
        source_retrieval=SourceRetrievalTrace(
            strategy=strategy,
            query_embedding_attempted=query_embedding.attempted,
            query_embedding_available=query_embedding.available,
            vector_attempted=repository_vector_attempted or local_vector_attempted,
            vector_candidate_count=vector_candidate_count,
            fallback_used=repository_vector_attempted,
        ),
    )


def _ranked_retrieval_strategy(
    *,
    candidates: list[RetrievedSource],
    vector_candidate_count: int,
) -> SourceRetrievalStrategy:
    if vector_candidate_count > 0:
        return "local_vector"
    if candidates:
        return "lexical"
    return "none"


def _can_use_local_vectors(
    *,
    query_embedding: QueryEmbeddingAttempt,
    embedding_records: Iterable[EmbeddingRecord],
) -> bool:
    return query_embedding.available and any(
        record.status == "ready" and record.vector for record in embedding_records
    )


def _rank_source_units(
    *,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    query: str,
    embedding_provider: EmbeddingProvider | None,
    query_vector: list[float] | None = None,
    resolve_query_vector: bool = True,
) -> list[SourceUnitMatch]:
    embedding_records_list = list(embedding_records)
    units = list(source_units)
    if not units:
        return []

    terms = _query_terms(query)
    if query_vector is None and resolve_query_vector:
        query_vector = _query_vector(
            query=query,
            embedding_records=embedding_records_list,
            embedding_provider=embedding_provider,
        )
    vectors_by_source_unit_id = {
        record.source_unit_id: record.vector
        for record in embedding_records_list
        if record.status == "ready" and record.vector
    }

    matches: list[SourceUnitMatch] = []
    for unit in units:
        lexical_score = _score_text(unit.search_text, terms)
        vector_score = None
        if query_vector is not None:
            document_vector = vectors_by_source_unit_id.get(unit.id)
            if document_vector is not None:
                vector_score = _cosine_similarity(query_vector, document_vector)

        if vector_score is not None:
            score = vector_score
        else:
            score = float(lexical_score)

        matches.append(
            SourceUnitMatch(
                source_unit=unit,
                score=score,
                lexical_score=lexical_score,
                vector_score=vector_score,
            )
        )

    return sorted(
        matches, key=lambda match: (match.score, match.lexical_score), reverse=True
    )


def select_source_excerpt(
    *,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    query: str,
    embedding_provider: EmbeddingProvider | None = None,
    retrieval_repository: RetrievalRepository | None = None,
    material_ids: Iterable[str] | None = None,
    max_chars: int = 420,
) -> SourceUnitExcerpt | None:
    records = list(embedding_records)
    query_vector = _query_vector(
        query=query,
        embedding_records=records,
        embedding_provider=embedding_provider,
    )
    match = None
    if (
        query_vector is not None
        and retrieval_repository is not None
        and material_ids is not None
    ):
        vector_matches = retrieval_repository.match_source_units(
            material_ids=material_ids,
            query_embedding=query_vector,
            limit=1,
            similarity_threshold=RAG_SIMILARITY_THRESHOLD,
        )
        if vector_matches:
            vector_match = vector_matches[0]
            terms = _query_terms(query)
            match = SourceUnitMatch(
                source_unit=vector_match.source_unit,
                score=vector_match.similarity,
                lexical_score=_score_text(vector_match.source_unit.search_text, terms),
                vector_score=vector_match.similarity,
            )
    if match is None:
        match = select_source_unit(
            source_units=source_units,
            embedding_records=records,
            query=query,
            embedding_provider=embedding_provider,
        )
    if match is None:
        return None

    text = match.source_unit.text[:max_chars].strip()
    if not text:
        return None
    return SourceUnitExcerpt(
        source_unit=match.source_unit,
        excerpt=text,
        score=match.score,
        lexical_score=match.lexical_score,
        vector_score=match.vector_score,
    )


def _score_text(text: str, terms: list[str]) -> int:
    if not terms:
        return 0

    lower_text = text.lower()
    return sum(1 for term in set(terms) if term in lower_text)


def _query_terms(query: str) -> list[str]:
    terms: list[str] = []
    current: list[str] = []
    for char in query.lower():
        if char.isalnum() or char == "_":
            current.append(char)
            continue
        if current:
            term = "".join(current)
            if len(term) >= 2:
                terms.append(term)
            current = []
    if current:
        term = "".join(current)
        if len(term) >= 2:
            terms.append(term)
    return terms


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _can_attempt_query_vector(
    *,
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None,
) -> bool:
    if embedding_provider is None:
        return False
    return any(
        record.status == "ready" and record.vector for record in embedding_records
    )


def _query_vector(
    *,
    query: str,
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None,
) -> list[float] | None:
    has_ready_embeddings = any(
        record.status == "ready" and record.vector for record in embedding_records
    )
    if not has_ready_embeddings or embedding_provider is None:
        return None

    try:
        return embedding_provider.embed_query(query)
    except EmbeddingProviderError:
        return None


def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None

    dot = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)
