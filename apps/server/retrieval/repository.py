from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import sqrt
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

    def clear(self) -> None:
        raise NotImplementedError


class InMemoryRetrievalRepository:
    def __init__(self) -> None:
        self._records_by_material_id: dict[str, RetrievalRecords] = {}

    def upsert_material_records(
        self, *, material_id: str, records: RetrievalRecords
    ) -> None:
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

    def match_source_units(
        self,
        *,
        material_ids: Iterable[str],
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
    ) -> list[VectorSourceUnitMatch]:
        records = self.records_for_materials(material_ids)
        units_by_id = {unit.id: unit for unit in records.source_units}
        matches: list[VectorSourceUnitMatch] = []

        for embedding_record in records.embedding_records:
            if embedding_record.status != "ready" or embedding_record.vector is None:
                continue
            source_unit = units_by_id.get(embedding_record.source_unit_id)
            if source_unit is None:
                continue
            similarity = _cosine_similarity(query_embedding, embedding_record.vector)
            if similarity is None or similarity < similarity_threshold:
                continue
            matches.append(
                VectorSourceUnitMatch(
                    source_unit=source_unit,
                    embedding_record=embedding_record,
                    similarity=similarity,
                )
            )

        return sorted(matches, key=lambda match: match.similarity, reverse=True)[:limit]

    def clear(self) -> None:
        self._records_by_material_id.clear()


def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None

    dot = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return dot / (left_norm * right_norm)
