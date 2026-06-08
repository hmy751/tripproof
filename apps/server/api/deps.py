from __future__ import annotations

from fastapi import Request

from server.materials.store import MaterialStore


def get_material_store(request: Request) -> MaterialStore:
    return request.app.state.material_store
