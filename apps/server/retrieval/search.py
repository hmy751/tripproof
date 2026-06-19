from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from server.core.config import RAG_SIMILARITY_THRESHOLD, RAG_TOP_K
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


@dataclass(frozen=True)
class SourceRetrievalTrace:
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
    if _can_attempt_repository_vector(
        query_embedding=query_embedding,
        retrieval_repository=retrieval_repository,
        material_ids=material_id_list,
    ):
        vector_context = _vector_search(
            target_id=target_id,
            query=query,
            query_embedding=query_embedding,
            retrieval_repository=retrieval_repository,
            material_ids=material_id_list,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        if vector_context is not None:
            return vector_context
        # 임베딩 벡터 검색이 매치를 못 줌 → 명시적 lexical fallback
        return _lexical_fallback(
            target_id=target_id,
            query=query,
            source_units=units,
            query_embedding=query_embedding,
            vector_attempted=True,
            top_k=top_k,
        )

    # 임베딩 자체가 없음 → 처음부터 lexical
    return _lexical_fallback(
        target_id=target_id,
        query=query,
        source_units=units,
        query_embedding=query_embedding,
        vector_attempted=False,
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


def _vector_search(
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
            query_embedding_attempted=query_embedding.attempted,
            query_embedding_available=query_embedding.available,
            vector_attempted=True,
            vector_candidate_count=len(vector_matches),
            fallback_used=False,
        ),
    )


def _lexical_fallback(
    *,
    target_id: str,
    query: str,
    source_units: Iterable[SourceUnit],
    query_embedding: QueryEmbeddingAttempt,
    vector_attempted: bool,
    top_k: int,
) -> RetrievedContext:
    matches = _rank_source_units(source_units=source_units, query=query)
    candidates = [
        RetrievedSource(
            target_id=target_id,
            query=query,
            source_unit=match.source_unit,
            score=match.score,
            lexical_score=match.lexical_score,
            vector_score=None,
        )
        for match in matches[:top_k]
        if match.score > 0
    ]
    return RetrievedContext(
        context=AnswerContext(target_id=target_id, query=query, candidates=candidates),
        source_retrieval=SourceRetrievalTrace(
            query_embedding_attempted=query_embedding.attempted,
            query_embedding_available=query_embedding.available,
            vector_attempted=vector_attempted,
            vector_candidate_count=0,
            fallback_used=vector_attempted,
        ),
    )


def _rank_source_units(
    *,
    source_units: Iterable[SourceUnit],
    query: str,
) -> list[SourceUnitMatch]:
    units = list(source_units)
    if not units:
        return []

    terms = _query_terms(query)
    matches: list[SourceUnitMatch] = []
    for unit in units:
        lexical_score = _score_text(unit.search_text, terms)
        matches.append(
            SourceUnitMatch(
                source_unit=unit,
                score=float(lexical_score),
                lexical_score=lexical_score,
            )
        )
    return sorted(matches, key=lambda match: match.lexical_score, reverse=True)


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
