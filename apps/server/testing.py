"""Test/eval support doubles. NOT imported by production code.

Production retrieval is Supabase-only (`server.retrieval.supabase`) and the
production answer composer is Ollama-only (`server.answers.library_chat`).
These in-memory stand-ins let tests and the offline eval smoke exercise the
full request flow without a live database or LLM. They are always injected
explicitly (via `create_app(...)` / `MaterialStore(...)`), never selected by
config — so they cannot masquerade as a production backend.
"""

from __future__ import annotations

from collections.abc import Iterable
from math import sqrt

from server.answers.library_chat import _missing_answer
from server.answers.models import ChatAnswer
from server.retrieval.models import AnswerContext
from server.retrieval.repository import RetrievalRecords, VectorSourceUnitMatch


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


class InMemoryRetrievalRepository:
    """In-memory `RetrievalRepository` double (stores records, ranks by cosine)."""

    def __init__(self) -> None:
        self._records_by_material_id: dict[str, RetrievalRecords] = {}

    def upsert_material_records(
        self, *, material_id: str, records: RetrievalRecords
    ) -> None:
        self._records_by_material_id[material_id] = records

    def records_for_materials(self, material_ids: Iterable[str]) -> RetrievalRecords:
        requested_ids = set(material_ids)
        source_units = []
        embedding_records = []
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


class MissingLibraryChatAnswerComposer:
    """Answer composer double that returns the missing-evidence answer (no LLM)."""

    def __init__(
        self,
        *,
        reason: str = "답변 생성기가 비활성화되어 있습니다.",
        backend: str = "missing",
    ) -> None:
        self._reason = reason
        self._backend = backend

    def compose(self, *, question: str, context: AnswerContext) -> ChatAnswer:
        return _missing_answer(reason=self._reason)

    def runtime_answer_model_snapshot(self) -> dict[str, str | None]:
        return {
            "backend": self._backend,
            "model": None,
        }
