"""Lexical (keyword) ranking of source units.

This is the fallback ranking used when vector retrieval is unavailable, and
`score_text`/`query_terms` are also the lexical_score primitives the vector
path reuses. Pure text scoring — no I/O, embedding, or repository dependency.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from server.retrieval.models import SourceUnit


@dataclass(frozen=True)
class SourceUnitMatch:
    source_unit: SourceUnit
    score: float
    lexical_score: int


def rank_source_units(
    *,
    source_units: Iterable[SourceUnit],
    query: str,
) -> list[SourceUnitMatch]:
    units = list(source_units)
    if not units:
        return []

    terms = query_terms(query)
    matches: list[SourceUnitMatch] = []
    for unit in units:
        lexical_score = score_text(unit.search_text, terms)
        matches.append(
            SourceUnitMatch(
                source_unit=unit,
                score=float(lexical_score),
                lexical_score=lexical_score,
            )
        )
    return sorted(matches, key=lambda match: match.lexical_score, reverse=True)


def score_text(text: str, terms: list[str]) -> int:
    if not terms:
        return 0

    lower_text = text.lower()
    return sum(1 for term in set(terms) if term in lower_text)


def query_terms(query: str) -> list[str]:
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
