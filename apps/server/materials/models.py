from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MaterialStatus = Literal["ready", "failed"]


@dataclass(frozen=True)
class PublicMaterial:
    id: str
    name: str
    file_name: str
    content_type: str | None
    status: MaterialStatus
    page_count: int | None
    preview: str | None
    error: str | None
