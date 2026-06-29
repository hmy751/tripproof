from __future__ import annotations

from dataclasses import dataclass, field

from server.extraction.models import Certification, EvidenceRef, EvidenceState


@dataclass(frozen=True)
class ChatAnswerItem:
    id: str
    label: str
    body: str
    evidence_state: EvidenceState
    value: str | None = None
    evidence: list[EvidenceRef] = field(default_factory=list)
    # certification은 candidate -> final 전이를 report에서 보기 위한 관측용
    # metadata다. API 응답 schema에는 싣지 않는다(제품 body에 debug/eval field 금지).
    certification: Certification | None = None


@dataclass(frozen=True)
class ChatAnswer:
    summary: str
    items: list[ChatAnswerItem] = field(default_factory=list)
