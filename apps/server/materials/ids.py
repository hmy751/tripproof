from __future__ import annotations

from uuid import uuid4


def new_material_id() -> str:
    return f"mat_{uuid4().hex[:12]}"
