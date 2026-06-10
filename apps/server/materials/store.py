from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from server.materials.observation import MaterialUploadObservationRecorder, embedding_record_build_facts
from server.retrieval.chunking import build_source_units
from server.retrieval.embeddings import (
    EmbeddingProfile,
    EmbeddingProvider,
    build_embedding_records,
    default_embedding_profile,
)
from server.retrieval.models import EmbeddingRecord, SourceUnit
from server.retrieval.repository import InMemoryRetrievalRepository, RetrievalRecords, RetrievalRepository
from server.schemas.materials import Material, MaterialStatus


@dataclass(frozen=True)
class StoredMaterial:
    id: str
    name: str
    file_name: str
    content_type: str | None
    status: MaterialStatus
    page_count: int
    text: str
    preview: str | None
    error: str | None
    source_units: list[SourceUnit]
    embedding_records: list[EmbeddingRecord]

    def public(self) -> Material:
        return Material(
            id=self.id,
            name=self.name,
            file_name=self.file_name,
            content_type=self.content_type,
            status=self.status,
            page_count=self.page_count if self.status == "ready" else None,
            preview=self.preview,
            error=self.error,
        )


class MaterialStore:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        embedding_profile: EmbeddingProfile | None = None,
        embedding_auto_generate: bool = False,
        retrieval_repository: RetrievalRepository | None = None,
    ) -> None:
        self._materials: dict[str, StoredMaterial] = {}
        self._embedding_provider = embedding_provider
        self._embedding_profile = embedding_profile or default_embedding_profile()
        self._embedding_auto_generate = embedding_auto_generate
        self._retrieval_repository = retrieval_repository or InMemoryRetrievalRepository()

    @property
    def embedding_provider(self) -> EmbeddingProvider | None:
        return self._embedding_provider

    @property
    def retrieval_repository(self) -> RetrievalRepository:
        return self._retrieval_repository

    def add_ready(
        self,
        *,
        name: str,
        file_name: str,
        content_type: str | None,
        page_count: int,
        text: str,
        preview: str,
        observation: MaterialUploadObservationRecorder | None = None,
    ) -> Material:
        material_id = _new_material_id()
        if observation is not None:
            observation.assign_material_id(material_id)
        try:
            source_units = build_source_units(material_id=material_id, file_name=file_name, text=text)
        except Exception:
            if observation is not None:
                observation.fail("source_unit_build", "source_unit_build_failed")
                observation.finalize("failed", failure_kind="source_unit_build_failed")
            raise
        if observation is not None:
            observation.succeed("source_unit_build", facts={"count": len(source_units)})

        try:
            embedding_records = build_embedding_records(
                source_units,
                provider=self._embedding_provider,
                profile=self._embedding_profile,
                generate=self._embedding_auto_generate,
            )
        except Exception:
            if observation is not None:
                observation.fail("embedding_record_build", "embedding_record_build_failed")
                observation.finalize("failed", failure_kind="embedding_record_build_failed")
            raise
        if observation is not None:
            observation.succeed("embedding_record_build", facts=embedding_record_build_facts(embedding_records))

        retrieval_records = RetrievalRecords(
            source_units=source_units,
            embedding_records=embedding_records,
        )
        material = StoredMaterial(
            id=material_id,
            name=name,
            file_name=file_name,
            content_type=content_type,
            status="ready",
            page_count=page_count,
            text=text,
            preview=preview,
            error=None,
            source_units=source_units,
            embedding_records=embedding_records,
        )
        try:
            self._retrieval_repository.upsert_material_records(material_id=material.id, records=retrieval_records)
        except Exception:
            if observation is not None:
                observation.fail("retrieval_repository_upsert", "repository_upsert_failed")
                observation.finalize("failed", failure_kind="repository_upsert_failed")
            raise
        if observation is not None:
            observation.succeed("retrieval_repository_upsert")
            observation.finalize("ready")
        self._materials[material.id] = material
        return material.public()

    def add_failed(
        self,
        *,
        name: str,
        file_name: str,
        content_type: str | None,
        error: str,
    ) -> Material:
        material = StoredMaterial(
            id=_new_material_id(),
            name=name,
            file_name=file_name,
            content_type=content_type,
            status="failed",
            page_count=0,
            text="",
            preview=None,
            error=error,
            source_units=[],
            embedding_records=[],
        )
        self._materials[material.id] = material
        return material.public()

    def list_public(self) -> list[Material]:
        return [material.public() for material in self._materials.values()]

    def ready_materials(self, material_ids: list[str] | None = None) -> list[StoredMaterial]:
        requested = set(material_ids or [])
        return [
            material
            for material in self._materials.values()
            if material.status == "ready" and (not requested or material.id in requested)
        ]

    def retrieval_records(self, material_ids: list[str] | None = None) -> RetrievalRecords:
        ready_material_ids = [material.id for material in self.ready_materials(material_ids)]
        return self._retrieval_repository.records_for_materials(ready_material_ids)

    def clear(self) -> None:
        self._materials.clear()
        self._retrieval_repository.clear()


def _new_material_id() -> str:
    return f"mat_{uuid4().hex[:12]}"
