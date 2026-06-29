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
class Certification:
    """코드가 소유하는 final state 판정 결과.

    `proposed_state`는 LLM 후보가 제안한 advisory 상태이고 `state`가 코드가 확정한
    최종 상태다. 둘을 함께 들고 다녀 report에서 candidate -> certification 전이를
    before/after로 볼 수 있게 한다(제품 응답 body에는 싣지 않는다).
    """

    state: EvidenceState
    reason: str
    proposed_state: EvidenceState
    evidence: list[EvidenceRef] = field(default_factory=list)
