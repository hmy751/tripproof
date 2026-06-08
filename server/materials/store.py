from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

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
    def __init__(self) -> None:
        self._materials: dict[str, StoredMaterial] = {}

    def add_ready(
        self,
        *,
        name: str,
        file_name: str,
        content_type: str | None,
        page_count: int,
        text: str,
        preview: str,
    ) -> Material:
        material = StoredMaterial(
            id=_new_material_id(),
            name=name,
            file_name=file_name,
            content_type=content_type,
            status="ready",
            page_count=page_count,
            text=text,
            preview=preview,
            error=None,
        )
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

    def clear(self) -> None:
        self._materials.clear()


def _new_material_id() -> str:
    return f"mat_{uuid4().hex[:12]}"
