from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from server.retrieval.models import EmbeddingRecord, SourceUnit


@dataclass(frozen=True)
class RetrievalRecords:
    source_units: list[SourceUnit]
    embedding_records: list[EmbeddingRecord]


class RetrievalRepository(Protocol):
    def upsert_material_records(self, *, material_id: str, records: RetrievalRecords) -> None:
        raise NotImplementedError

    def records_for_materials(self, material_ids: Iterable[str]) -> RetrievalRecords:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class InMemoryRetrievalRepository:
    def __init__(self) -> None:
        self._records_by_material_id: dict[str, RetrievalRecords] = {}

    def upsert_material_records(self, *, material_id: str, records: RetrievalRecords) -> None:
        self._records_by_material_id[material_id] = records

    def records_for_materials(self, material_ids: Iterable[str]) -> RetrievalRecords:
        requested_ids = set(material_ids)
        source_units: list[SourceUnit] = []
        embedding_records: list[EmbeddingRecord] = []

        for material_id in requested_ids:
            records = self._records_by_material_id.get(material_id)
            if records is None:
                continue
            source_units.extend(records.source_units)
            embedding_records.extend(records.embedding_records)

        return RetrievalRecords(
            source_units=source_units,
            embedding_records=embedding_records,
        )

    def clear(self) -> None:
        self._records_by_material_id.clear()
