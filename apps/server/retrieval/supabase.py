from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from server.core.config import (
    SUPABASE_INSERT_BATCH_SIZE,
    SUPABASE_REST_TIMEOUT_SECONDS,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)
from server.retrieval.models import EmbeddingRecord, SourceUnit
from server.retrieval.repository import RetrievalRecords, RetrievalRepository, VectorSourceUnitMatch


class SupabaseRetrievalError(RuntimeError):
    pass


@dataclass(frozen=True)
class SupabaseRetrievalConfig:
    url: str
    service_role_key: str
    insert_batch_size: int = SUPABASE_INSERT_BATCH_SIZE
    timeout_seconds: float = SUPABASE_REST_TIMEOUT_SECONDS


class SupabaseRetrievalRepository:
    def __init__(self, config: SupabaseRetrievalConfig) -> None:
        if not config.url or not config.service_role_key:
            raise SupabaseRetrievalError(
                "TRIPPROOF_SUPABASE_URL and TRIPPROOF_SUPABASE_SERVICE_ROLE_KEY are required."
            )
        self._config = config
        self._base_url = config.url.rstrip("/")

    def upsert_material_records(self, *, material_id: str, records: RetrievalRecords) -> None:
        self._delete_rows(
            table="tripproof_source_units",
            query={"material_id": f"eq.{material_id}"},
        )
        self._insert_batches(
            table="tripproof_source_units",
            rows=[_source_unit_to_row(unit) for unit in records.source_units],
        )
        self._insert_batches(
            table="tripproof_source_embeddings",
            rows=[_embedding_record_to_row(record, material_id=material_id) for record in records.embedding_records],
        )

    def records_for_materials(self, material_ids: Iterable[str]) -> RetrievalRecords:
        requested_ids = list(dict.fromkeys(material_ids))
        if not requested_ids:
            return RetrievalRecords(source_units=[], embedding_records=[])

        source_unit_rows = self._select_rows(
            table="tripproof_source_units",
            query={
                "material_id": _in_filter(requested_ids),
                "select": "*",
                "order": "material_id.asc,page.asc,unit_index.asc",
            },
        )
        embedding_rows = self._select_rows(
            table="tripproof_source_embeddings",
            query={
                "material_id": _in_filter(requested_ids),
                "select": "*",
            },
        )

        return RetrievalRecords(
            source_units=[_source_unit_from_row(row) for row in source_unit_rows],
            embedding_records=[_embedding_record_from_row(row) for row in embedding_rows],
        )

    def match_source_units(
        self,
        *,
        material_ids: Iterable[str],
        query_embedding: list[float],
        limit: int,
        similarity_threshold: float,
    ) -> list[VectorSourceUnitMatch]:
        requested_ids = list(dict.fromkeys(material_ids))
        if not requested_ids:
            return []

        rows = self._rpc(
            "match_tripproof_source_units",
            {
                "query_embedding": query_embedding,
                "match_count": limit,
                "p_material_ids": requested_ids,
                "similarity_threshold": similarity_threshold,
            },
        )

        return [
            VectorSourceUnitMatch(
                source_unit=_source_unit_from_match_row(row),
                embedding_record=_embedding_record_from_match_row(row),
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]

    def clear(self) -> None:
        raise SupabaseRetrievalError("Supabase retrieval repository does not support global clear().")

    def _insert_batches(self, *, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        batch_size = max(1, self._config.insert_batch_size)
        for start in range(0, len(rows), batch_size):
            self._request(
                path=f"/rest/v1/{table}",
                method="POST",
                body=rows[start : start + batch_size],
                extra_headers={"Prefer": "return=minimal"},
            )

    def _select_rows(self, *, table: str, query: dict[str, str]) -> list[dict[str, Any]]:
        response = self._request(
            path=f"/rest/v1/{table}?{parse.urlencode(query, safe='(),.*')}",
            method="GET",
        )
        return _ensure_list(response)

    def _delete_rows(self, *, table: str, query: dict[str, str]) -> None:
        query_string = f"?{parse.urlencode(query, safe='(),.*')}" if query else ""
        self._request(
            path=f"/rest/v1/{table}{query_string}",
            method="DELETE",
            extra_headers={"Prefer": "return=minimal"},
        )

    def _rpc(self, function_name: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        response = self._request(
            path=f"/rest/v1/rpc/{function_name}",
            method="POST",
            body=body,
        )
        return _ensure_list(response)

    def _request(
        self,
        *,
        path: str,
        method: str,
        body: object | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> object:
        headers = {
            "apikey": self._config.service_role_key,
            "Authorization": f"Bearer {self._config.service_role_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        encoded_body = None if body is None else json.dumps(body).encode("utf-8")
        http_request = request.Request(
            f"{self._base_url}{path}",
            data=encoded_body,
            headers=headers,
            method=method,
        )

        try:
            with request.urlopen(http_request, timeout=self._config.timeout_seconds) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SupabaseRetrievalError(f"Supabase {method} {path} failed: {detail}") from exc
        except error.URLError as exc:
            raise SupabaseRetrievalError(f"Supabase {method} {path} failed: {exc}") from exc

        if not raw:
            return []
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SupabaseRetrievalError("Supabase response was not valid JSON.") from exc


def create_supabase_retrieval_repository_from_config() -> RetrievalRepository:
    return SupabaseRetrievalRepository(
        SupabaseRetrievalConfig(
            url=SUPABASE_URL,
            service_role_key=SUPABASE_SERVICE_ROLE_KEY,
        )
    )


def _source_unit_to_row(unit: SourceUnit) -> dict[str, Any]:
    return {
        "id": unit.id,
        "material_id": unit.material_id,
        "file_name": unit.file_name,
        "page": unit.page,
        "unit_index": unit.unit_index,
        "locator": unit.locator,
        "text": unit.text,
        "search_text": unit.search_text,
        "start_offset": unit.start,
        "end_offset": unit.end,
        "metadata": unit.metadata,
    }


def _embedding_record_to_row(record: EmbeddingRecord, *, material_id: str) -> dict[str, Any]:
    return {
        "id": record.id,
        "material_id": material_id,
        "source_unit_id": record.source_unit_id,
        "provider": record.provider,
        "model": record.model,
        "dimensions": record.dimensions,
        "embedding": record.vector,
        "status": record.status,
        "error": record.error,
    }


def _source_unit_from_row(row: dict[str, Any]) -> SourceUnit:
    return SourceUnit(
        id=str(row["id"]),
        material_id=str(row["material_id"]),
        file_name=str(row["file_name"]),
        page=int(row["page"]),
        unit_index=int(row["unit_index"]),
        locator=str(row["locator"]),
        text=str(row["text"]),
        search_text=str(row["search_text"]),
        start=int(row["start_offset"]),
        end=int(row["end_offset"]),
        metadata=dict(row.get("metadata") or {}),
    )


def _embedding_record_from_row(row: dict[str, Any]) -> EmbeddingRecord:
    return EmbeddingRecord(
        id=str(row["id"]),
        source_unit_id=str(row["source_unit_id"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        dimensions=int(row["dimensions"]),
        vector=_vector_from_value(row.get("embedding")),
        status=row["status"],
        error=row.get("error"),
    )


def _source_unit_from_match_row(row: dict[str, Any]) -> SourceUnit:
    return SourceUnit(
        id=str(row["source_unit_id"]),
        material_id=str(row["material_id"]),
        file_name=str(row["file_name"]),
        page=int(row["page"]),
        unit_index=int(row["unit_index"]),
        locator=str(row["locator"]),
        text=str(row["text"]),
        search_text=str(row["search_text"]),
        start=int(row["start_offset"]),
        end=int(row["end_offset"]),
        metadata=dict(row.get("metadata") or {}),
    )


def _embedding_record_from_match_row(row: dict[str, Any]) -> EmbeddingRecord:
    return EmbeddingRecord(
        id=str(row["embedding_id"]),
        source_unit_id=str(row["source_unit_id"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        dimensions=int(row["dimensions"]),
        vector=None,
        status="ready",
    )


def _ensure_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SupabaseRetrievalError("Supabase response was not a list.")
    return [dict(item) for item in value]


def _vector_from_value(value: object) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        normalized = value.strip().removeprefix("[").removesuffix("]")
        if not normalized:
            return []
        return [float(item.strip()) for item in normalized.split(",")]
    raise SupabaseRetrievalError("Supabase embedding value was not a vector.")


def _in_filter(values: list[str]) -> str:
    escaped = [value.replace('"', '\\"') for value in values]
    quoted = [f'"{value}"' for value in escaped]
    return f"in.({','.join(quoted)})"
