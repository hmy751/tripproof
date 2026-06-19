from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from server.retrieval.models import EmbeddingRecord, SourceUnit


@dataclass(frozen=True)
class RetrievalRecords:
    source_units: list[SourceUnit]
    embedding_records: list[EmbeddingRecord]


@dataclass(frozen=True)
class VectorSourceUnitMatch:
    source_unit: SourceUnit
    embedding_record: EmbeddingRecord
    similarity: float


class RetrievalRepository(Protocol):
    def upsert_material_records(
        self, *, material_id: str, records: RetrievalRecords
    ) -> None:
        raise NotImplementedError

    def records_for_materials(self, material_ids: Iterable[str]) -> RetrievalRecords:
        raise NotImplementedError

    def match_source_units(
        self,
        *,
        material_ids: Iterable[str],
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
    ) -> list[VectorSourceUnitMatch]:
        raise NotImplementedError
