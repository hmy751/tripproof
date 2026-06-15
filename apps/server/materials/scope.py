from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialScope:
    selected_ids: tuple[str, ...] | None = None

    @classmethod
    def from_material_ids(cls, material_ids: list[str] | None) -> MaterialScope:
        if material_ids is None:
            return cls.all_ready()
        return cls.selected(material_ids)

    @classmethod
    def all_ready(cls) -> MaterialScope:
        return cls(selected_ids=None)

    @classmethod
    def selected(cls, material_ids: list[str]) -> MaterialScope:
        return cls(selected_ids=tuple(dict.fromkeys(material_ids)))

    def includes(self, material_id: str) -> bool:
        if self.selected_ids is None:
            return True
        return material_id in set(self.selected_ids)
