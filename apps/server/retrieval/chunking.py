from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    start: int
    end: int


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 160) -> list[TextChunk]:
    stripped = text.strip()
    if not stripped:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    while start < len(stripped):
        end = min(start + chunk_size, len(stripped))
        chunks.append(TextChunk(text=stripped[start:end], start=start, end=end))
        if end == len(stripped):
            break
        start = end - overlap
    return chunks
