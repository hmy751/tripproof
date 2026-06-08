from __future__ import annotations

import re
from collections.abc import Iterable

from server.retrieval.chunking import chunk_text


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


def _score_text(text: str, terms: list[str]) -> int:
    if not terms:
        return 0

    lower_text = text.lower()
    return sum(lower_text.count(term) for term in terms)
