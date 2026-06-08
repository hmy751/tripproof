from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
import re
from collections.abc import Iterable

from server.retrieval.chunking import chunk_text
from server.retrieval.embeddings import EmbeddingProvider, EmbeddingProviderError
from server.retrieval.models import EmbeddingRecord, SourceUnit


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


def select_excerpt(texts: Iterable[str], query: str, *, max_chars: int = 420) -> str | None:
    normalized = re.sub(r"\s+", " ", "\n\n".join(texts)).strip()
    if not normalized:
        return None

    terms = [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term) >= 2]
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
    embedding_records_list = list(embedding_records)
    units = list(source_units)
    if not units:
        return None

    terms = _query_terms(query)
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

    best: SourceUnitMatch | None = None
    for unit in units:
        lexical_score = _score_text(unit.search_text, terms)
        vector_score = None
        if query_vector is not None:
            document_vector = vectors_by_source_unit_id.get(unit.id)
            if document_vector is not None:
                vector_score = _cosine_similarity(query_vector, document_vector)

        score = float(lexical_score)
        if vector_score is not None:
            score += max(vector_score, 0.0)

        candidate = SourceUnitMatch(
            source_unit=unit,
            score=score,
            lexical_score=lexical_score,
            vector_score=vector_score,
        )
        if best is None or candidate.score > best.score:
            best = candidate

    return best


def select_source_excerpt(
    *,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    query: str,
    embedding_provider: EmbeddingProvider | None = None,
    max_chars: int = 420,
) -> SourceUnitExcerpt | None:
    match = select_source_unit(
        source_units=source_units,
        embedding_records=embedding_records,
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
    return sum(lower_text.count(term) for term in terms)


def _query_terms(query: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term) >= 2]


def _query_vector(
    *,
    query: str,
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None,
) -> list[float] | None:
    has_ready_embeddings = any(record.status == "ready" and record.vector for record in embedding_records)
    if not has_ready_embeddings or embedding_provider is None:
        return None

    try:
        return embedding_provider.embed_query(query)
    except EmbeddingProviderError:
        return None


def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None

    dot = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)
