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
class Caveat:
    """의미 층(LLM/relation extractor)이 낸 '이 값을 지배하는 조건' 역할.

    코드가 `kind`나 page 근접으로 추정해 만드는 게 아니라, 의미 층이 후보 원문에서
    식별해 낸 값↔조건 관계다(`06-evidence-relation-extraction.md`). 코드 certification은
    이 역할이 붙었는지와 그 snippet이 원문에 grounding되는지(구조)만 보고 상태를 내린다 —
    조건 문장의 의미를 코드가 다시 분류하지 않는다.
    """

    source_unit_id: str | None
    snippet: str | None
    text: str | None


@dataclass(frozen=True)
class Certification:
    """코드가 소유하는 final state 판정 결과.

    `proposed_state`는 LLM 후보가 제안한 advisory 상태이고 `state`가 코드가 확정한
    최종 상태다. 둘을 함께 들고 다녀 report에서 candidate -> certification 전이를
    before/after로 볼 수 있게 한다(제품 응답 body에는 싣지 않는다).

    `caveat`은 `limited_by_caveat` 강등 때 읽은, 원문에 grounding된
    조건 근거다. 관측용이며 제품 응답 body에는 싣지 않는다.
    """

    state: EvidenceState
    reason: str
    proposed_state: EvidenceState
    evidence: list[EvidenceRef] = field(default_factory=list)
    caveat: EvidenceRef | None = None
