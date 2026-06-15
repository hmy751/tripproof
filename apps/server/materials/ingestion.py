from __future__ import annotations

from typing import Protocol

from server.retrieval.models import EmbeddingRecord


class MaterialIngestionEvents(Protocol):
    def material_id_assigned(self, material_id: str) -> None:
        raise NotImplementedError

    def source_unit_build_failed(self) -> None:
        raise NotImplementedError

    def source_units_built(self, *, count: int) -> None:
        raise NotImplementedError

    def embedding_record_build_failed(self) -> None:
        raise NotImplementedError

    def embedding_records_built(self, *, records: list[EmbeddingRecord]) -> None:
        raise NotImplementedError

    def retrieval_records_upsert_failed(
        self,
        *,
        source_unit_count: int,
        embedding_record_count: int,
    ) -> None:
        raise NotImplementedError

    def retrieval_records_upserted(
        self,
        *,
        source_unit_count: int,
        embedding_record_count: int,
    ) -> None:
        raise NotImplementedError

    def material_ready(self) -> None:
        raise NotImplementedError


class NoopMaterialIngestionEvents:
    def material_id_assigned(self, material_id: str) -> None:
        return None

    def source_unit_build_failed(self) -> None:
        return None

    def source_units_built(self, *, count: int) -> None:
        return None

    def embedding_record_build_failed(self) -> None:
        return None

    def embedding_records_built(self, *, records: list[EmbeddingRecord]) -> None:
        return None

    def retrieval_records_upsert_failed(
        self,
        *,
        source_unit_count: int,
        embedding_record_count: int,
    ) -> None:
        return None

    def retrieval_records_upserted(
        self,
        *,
        source_unit_count: int,
        embedding_record_count: int,
    ) -> None:
        return None

    def material_ready(self) -> None:
        return None
