from __future__ import annotations

from dataclasses import dataclass

from server.materials.ids import new_material_id
from server.materials.ingestion import (
    MaterialIngestionPipeline,
    MaterialIngestionEvents,
    NoopMaterialIngestionEvents,
)
from server.materials.layout import PageLayout
from server.materials.models import MaterialStatus, PublicMaterial
from server.materials.scope import MaterialScope
from server.retrieval.embeddings import (
    EmbeddingProfile,
    EmbeddingProvider,
    default_embedding_profile,
)
from server.retrieval.models import EmbeddingRecord, SourceUnit
from server.retrieval.repository import (
    ClearableRetrievalRepository,
    InMemoryRetrievalRepository,
    RetrievalRecords,
    RetrievalRepository,
)


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

    def public(self) -> PublicMaterial:
        return PublicMaterial(
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
        retrieval_backend: str | None = None,
    ) -> None:
        self._materials: dict[str, StoredMaterial] = {}
        self._embedding_provider = embedding_provider
        self._embedding_profile = embedding_profile or default_embedding_profile()
        self._embedding_auto_generate = embedding_auto_generate
        self._retrieval_repository = (
            retrieval_repository or InMemoryRetrievalRepository()
        )
        if retrieval_backend is not None:
            self._retrieval_backend = retrieval_backend
        elif retrieval_repository is None or isinstance(
            retrieval_repository, InMemoryRetrievalRepository
        ):
            self._retrieval_backend = "memory"
        else:
            self._retrieval_backend = "custom"
        self._ingestion_pipeline = MaterialIngestionPipeline(
            embedding_provider=self._embedding_provider,
            embedding_profile=self._embedding_profile,
            embedding_auto_generate=self._embedding_auto_generate,
            retrieval_repository=self._retrieval_repository,
        )

    @property
    def embedding_provider(self) -> EmbeddingProvider | None:
        return self._embedding_provider

    @property
    def embedding_profile(self) -> EmbeddingProfile:
        if self._embedding_provider is not None:
            return self._embedding_provider.profile
        return self._embedding_profile

    @property
    def embedding_auto_generate(self) -> bool:
        return self._embedding_auto_generate

    @property
    def retrieval_backend(self) -> str:
        return self._retrieval_backend

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
        layout_pages: tuple[PageLayout, ...] = (),
        ingestion_events: MaterialIngestionEvents | None = None,
    ) -> PublicMaterial:
        events = ingestion_events or NoopMaterialIngestionEvents()
        ingestion_result = self._ingestion_pipeline.prepare_ready_material(
            file_name=file_name,
            text=text,
            layout_pages=layout_pages,
            events=events,
        )
        material = StoredMaterial(
            id=ingestion_result.material_id,
            name=name,
            file_name=file_name,
            content_type=content_type,
            status="ready",
            page_count=page_count,
            text=text,
            preview=preview,
            error=None,
            source_units=ingestion_result.source_units,
            embedding_records=ingestion_result.embedding_records,
        )
        events.material_ready()
        self._materials[material.id] = material
        return material.public()

    def add_failed(
        self,
        *,
        name: str,
        file_name: str,
        content_type: str | None,
        error: str,
    ) -> PublicMaterial:
        material = StoredMaterial(
            id=new_material_id(),
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

    def list_public(self) -> list[PublicMaterial]:
        return [material.public() for material in self._materials.values()]

    def ready_materials(
        self, material_ids: list[str] | None = None
    ) -> list[StoredMaterial]:
        scope = MaterialScope.from_material_ids(material_ids)
        return [
            material
            for material in self._materials.values()
            if material.status == "ready" and scope.includes(material.id)
        ]

    def retrieval_records(
        self, material_ids: list[str] | None = None
    ) -> RetrievalRecords:
        ready_material_ids = [
            material.id for material in self.ready_materials(material_ids)
        ]
        return self._retrieval_repository.records_for_materials(ready_material_ids)

    def clear(self) -> None:
        self._materials.clear()
        if isinstance(self._retrieval_repository, ClearableRetrievalRepository):
            self._retrieval_repository.clear()
