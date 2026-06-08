from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class SourceUnit:
    id: str
    material_id: str
    file_name: str
    page: int
    unit_index: int
    locator: str
    text: str
    search_text: str
    start: int
    end: int
    metadata: dict[str, object] = field(default_factory=dict)


EmbeddingStatus = Literal["pending", "ready", "failed"]


@dataclass(frozen=True)
class EmbeddingRecord:
    id: str
    source_unit_id: str
    provider: str
    model: str
    dimensions: int
    vector: list[float] | None
    status: EmbeddingStatus
    error: str | None = None
