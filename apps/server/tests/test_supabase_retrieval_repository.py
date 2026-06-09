from __future__ import annotations

from typing import Any

from server.retrieval.models import EmbeddingRecord, SourceUnit
from server.retrieval.repository import RetrievalRecords
from server.retrieval.supabase import SupabaseRetrievalConfig, SupabaseRetrievalRepository


def test_supabase_repository_upserts_tripproof_source_units_and_embeddings() -> None:
    repository = FakeSupabaseRetrievalRepository()
    source_unit = _source_unit()
    embedding = _embedding_record(source_unit_id=source_unit.id)

    repository.upsert_material_records(
        material_id="mat_1",
        records=RetrievalRecords(source_units=[source_unit], embedding_records=[embedding]),
    )

    assert repository.requests[0]["method"] == "DELETE"
    assert repository.requests[0]["path"] == "/rest/v1/tripproof_source_units?material_id=eq.mat_1"
    assert repository.requests[1]["path"] == "/rest/v1/tripproof_source_units"
    assert repository.requests[1]["body"][0]["id"] == source_unit.id
    assert repository.requests[1]["body"][0]["text"] == source_unit.text
    assert repository.requests[2]["path"] == "/rest/v1/tripproof_source_embeddings"
    assert repository.requests[2]["body"][0]["source_unit_id"] == source_unit.id
    assert repository.requests[2]["body"][0]["embedding"] == [1.0, 0.0]


def test_supabase_repository_maps_rpc_matches_to_source_units() -> None:
    repository = FakeSupabaseRetrievalRepository(
        rpc_response=[
            {
                "source_unit_id": "su_1",
                "material_id": "mat_1",
                "file_name": "booking.pdf",
                "page": 1,
                "unit_index": 1,
                "locator": "booking.pdf p.1 u.1",
                "text": "Show your booking confirmation.",
                "search_text": "Show your booking confirmation.",
                "start_offset": 0,
                "end_offset": 31,
                "metadata": {"kind": "pdf"},
                "embedding_id": "emb_1",
                "provider": "ollama",
                "model": "nomic-embed-text-v2-moe",
                "dimensions": 768,
                "similarity": 0.87,
            }
        ]
    )

    matches = repository.match_source_units(
        material_ids=["mat_1"],
        query_embedding=[1.0, 0.0],
        limit=3,
        similarity_threshold=0.2,
    )

    assert repository.requests[0]["path"] == "/rest/v1/rpc/match_tripproof_source_units"
    assert repository.requests[0]["body"]["p_material_ids"] == ["mat_1"]
    assert matches[0].source_unit.id == "su_1"
    assert matches[0].source_unit.text == "Show your booking confirmation."
    assert matches[0].embedding_record.id == "emb_1"
    assert matches[0].similarity == 0.87


def test_supabase_repository_reads_pgvector_string_values() -> None:
    repository = FakeSupabaseRetrievalRepository(
        select_responses={
            "tripproof_source_units": [
                {
                    "id": "su_1",
                    "material_id": "mat_1",
                    "file_name": "booking.pdf",
                    "page": 1,
                    "unit_index": 1,
                    "locator": "booking.pdf p.1 u.1",
                    "text": "Show your booking confirmation.",
                    "search_text": "Show your booking confirmation.",
                    "start_offset": 0,
                    "end_offset": 31,
                    "metadata": {},
                }
            ],
            "tripproof_source_embeddings": [
                {
                    "id": "emb_1",
                    "material_id": "mat_1",
                    "source_unit_id": "su_1",
                    "provider": "ollama",
                    "model": "nomic-embed-text-v2-moe",
                    "dimensions": 2,
                    "embedding": "[1,0]",
                    "status": "ready",
                    "error": None,
                }
            ],
        }
    )

    records = repository.records_for_materials(["mat_1"])

    assert records.source_units[0].id == "su_1"
    assert records.embedding_records[0].vector == [1.0, 0.0]


class FakeSupabaseRetrievalRepository(SupabaseRetrievalRepository):
    def __init__(
        self,
        *,
        rpc_response: list[dict[str, Any]] | None = None,
        select_responses: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        super().__init__(
            SupabaseRetrievalConfig(
                url="https://example.supabase.co",
                service_role_key="test-key",
            )
        )
        self.requests: list[dict[str, Any]] = []
        self._rpc_response = rpc_response or []
        self._select_responses = select_responses or {}

    def _request(self, *, path, method, body=None, extra_headers=None):
        self.requests.append(
            {
                "path": path,
                "method": method,
                "body": body,
                "extra_headers": extra_headers,
            }
        )
        if path == "/rest/v1/rpc/match_tripproof_source_units":
            return self._rpc_response
        for table, response in self._select_responses.items():
            if path.startswith(f"/rest/v1/{table}?") and method == "GET":
                return response
        return []


def _source_unit() -> SourceUnit:
    return SourceUnit(
        id="su_1",
        material_id="mat_1",
        file_name="booking.pdf",
        page=1,
        unit_index=1,
        locator="booking.pdf p.1 u.1",
        text="Show your booking confirmation.",
        search_text="Show your booking confirmation.",
        start=0,
        end=31,
        metadata={"kind": "pdf"},
    )


def _embedding_record(*, source_unit_id: str) -> EmbeddingRecord:
    return EmbeddingRecord(
        id="emb_1",
        source_unit_id=source_unit_id,
        provider="ollama",
        model="nomic-embed-text-v2-moe",
        dimensions=768,
        vector=[1.0, 0.0],
        status="ready",
    )
