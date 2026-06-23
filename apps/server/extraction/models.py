from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EvidenceState(StrEnum):
    SUPPORTED = "supported"
    NEEDS_REVIEW = "needs_review"
    MISSING = "missing"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class EvidenceRef:
    material_id: str
    source_unit_id: str
    label: str
    locator: str
    snippet: str
