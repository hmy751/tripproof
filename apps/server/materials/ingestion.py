from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.materials.ids import new_material_id
from server.materials.layout import PageLayout
from server.retrieval.chunking import build_source_units
from server.retrieval.embeddings import (
    EmbeddingProfile,
    EmbeddingProvider,
    build_embedding_records,
)
from server.retrieval.models import EmbeddingRecord
from server.retrieval.models import SourceUnit
from server.retrieval.repository import RetrievalRecords, RetrievalRepository


@dataclass(frozen=True)
class ReadyMaterialIngestionResult:
    material_id: str
    source_units: list[SourceUnit]
    embedding_records: list[EmbeddingRecord]


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


class MaterialIngestionPipeline:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None,
        embedding_profile: EmbeddingProfile,
        embedding_auto_generate: bool,
        retrieval_repository: RetrievalRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._embedding_profile = embedding_profile
        self._embedding_auto_generate = embedding_auto_generate
        self._retrieval_repository = retrieval_repository

    def prepare_ready_material(
        self,
        *,
        file_name: str,
        text: str,
        layout_pages: tuple[PageLayout, ...] = (),
        events: MaterialIngestionEvents,
    ) -> ReadyMaterialIngestionResult:
        material_id = new_material_id()
        events.material_id_assigned(material_id)
        try:
            source_units = build_source_units(
                material_id=material_id,
                file_name=file_name,
                text=text,
                layout_pages=layout_pages,
            )
        except Exception:
            events.source_unit_build_failed()
            raise
        events.source_units_built(count=len(source_units))

        try:
            embedding_records = build_embedding_records(
                source_units,
                provider=self._embedding_provider,
                profile=self._embedding_profile,
                generate=self._embedding_auto_generate,
            )
        except Exception:
            events.embedding_record_build_failed()
            raise
        events.embedding_records_built(records=embedding_records)

        retrieval_records = RetrievalRecords(
            source_units=source_units,
            embedding_records=embedding_records,
        )
        try:
            self._retrieval_repository.upsert_material_records(
                material_id=material_id, records=retrieval_records
            )
        except Exception:
            events.retrieval_records_upsert_failed(
                source_unit_count=len(source_units),
                embedding_record_count=len(embedding_records),
            )
            raise
        events.retrieval_records_upserted(
            source_unit_count=len(source_units),
            embedding_record_count=len(embedding_records),
        )

        return ReadyMaterialIngestionResult(
            material_id=material_id,
            source_units=source_units,
            embedding_records=embedding_records,
        )
