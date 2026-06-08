from __future__ import annotations

from enum import StrEnum


class EvidenceState(StrEnum):
    SUPPORTED = "supported"
    NEEDS_REVIEW = "needs_review"
    MISSING = "missing"
    CONFLICT = "conflict"
