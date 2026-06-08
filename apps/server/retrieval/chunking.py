from __future__ import annotations

import re
from dataclasses import dataclass

from server.retrieval.models import SourceUnit


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


_PAGE_MARKER_RE = re.compile(r"(?m)^\[page (?P<page>\d+)\]\s*$")


def build_source_units(
    *,
    material_id: str,
    file_name: str,
    text: str,
    chunk_size: int = 1200,
    overlap: int = 160,
) -> list[SourceUnit]:
    units: list[SourceUnit] = []
    unit_index = 1

    for page, page_text in _iter_page_texts(text):
        for chunk in chunk_text(page_text, chunk_size=chunk_size, overlap=overlap):
            locator = _locator(file_name=file_name, page=page, unit_index=unit_index)
            units.append(
                SourceUnit(
                    id=f"su_{material_id}_{page}_{unit_index}",
                    material_id=material_id,
                    file_name=file_name,
                    page=page,
                    unit_index=unit_index,
                    locator=locator,
                    text=chunk.text,
                    search_text=_normalize_search_text(chunk.text),
                    start=chunk.start,
                    end=chunk.end,
                    metadata={"page": page},
                )
            )
            unit_index += 1

    return units


def _iter_page_texts(text: str) -> list[tuple[int, str]]:
    stripped = text.strip()
    if not stripped:
        return []

    markers = list(_PAGE_MARKER_RE.finditer(stripped))
    if not markers:
        return [(1, stripped)]

    pages: list[tuple[int, str]] = []
    for index, marker in enumerate(markers):
        page = int(marker.group("page"))
        body_start = marker.end()
        body_end = markers[index + 1].start() if index + 1 < len(markers) else len(stripped)
        page_text = stripped[body_start:body_end].strip()
        if page_text:
            pages.append((page, page_text))
    return pages


def _locator(*, file_name: str, page: int, unit_index: int) -> str:
    return f"{file_name} p.{page} u.{unit_index}"


def _normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
