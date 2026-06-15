from __future__ import annotations

from dataclasses import dataclass

from server.materials.store import MaterialStore, StoredMaterial


@dataclass(frozen=True)
class MaterialScopeSelection:
    ready_materials: list[StoredMaterial]

    @property
    def ready_material_ids(self) -> list[str]:
        return [material.id for material in self.ready_materials]

    @property
    def page_count(self) -> int:
        return sum(material.page_count for material in self.ready_materials)

    @property
    def char_count(self) -> int:
        return sum(len(material.text) for material in self.ready_materials)

    @property
    def is_empty(self) -> bool:
        return not self.ready_materials


class MaterialScopeSelector:
    def __init__(self, store: MaterialStore) -> None:
        self._store = store

    def select(self, material_ids: list[str] | None) -> MaterialScopeSelection:
        return MaterialScopeSelection(
            ready_materials=self._store.ready_materials(material_ids)
        )
