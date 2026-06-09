from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class FactTarget:
    id: str
    label: str
    query: str


@dataclass(frozen=True)
class FactProposal:
    target_id: str
    label: str
    value: str | None
    evidence_state: EvidenceState
    evidence_snippet: str | None = None
    source_unit_id: str | None = None
    sensitive: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class FactCandidate:
    id: str
    label: str
    value: str | None
    evidence_state: EvidenceState
    evidence: list[EvidenceRef] = field(default_factory=list)
    sensitive: bool = False
    reason: str | None = None
