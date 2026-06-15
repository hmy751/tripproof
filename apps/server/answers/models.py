from __future__ import annotations

from dataclasses import dataclass, field

from server.extraction.models import EvidenceRef, EvidenceState


@dataclass(frozen=True)
class ChatAnswerItem:
    id: str
    label: str
    body: str
    evidence_state: EvidenceState
    value: str | None = None
    evidence: list[EvidenceRef] = field(default_factory=list)


@dataclass(frozen=True)
class ChatAnswer:
    summary: str
    items: list[ChatAnswerItem] = field(default_factory=list)
