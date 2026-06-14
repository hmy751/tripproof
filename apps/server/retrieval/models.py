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


@dataclass(frozen=True)
class RetrievedSource:
    target_id: str
    query: str
    source_unit: SourceUnit
    score: float
    lexical_score: int
    vector_score: float | None


@dataclass(frozen=True)
class AnswerContext:
    target_id: str
    query: str
    candidates: list[RetrievedSource]


RetrievalCandidate = RetrievedSource
ContextPack = AnswerContext


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
