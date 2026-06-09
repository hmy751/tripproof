from __future__ import annotations

from pydantic import Field

from server.extraction.models import EvidenceState, FactCandidate
from server.schemas.base import ApiModel
from server.schemas.facts import EvidenceRefResponse


class ChatAnswerItemResponse(ApiModel):
    id: str
    label: str
    body: str
    evidence_state: EvidenceState = Field(alias="evidenceState")
    value: str | None = None
    evidence: list[EvidenceRefResponse] = Field(default_factory=list)

    @classmethod
    def from_fact(cls, *, fact: FactCandidate, body: str) -> ChatAnswerItemResponse:
        return cls(
            id=fact.id,
            label=fact.label,
            body=body,
            evidence_state=fact.evidence_state,
            value=fact.value,
            evidence=[EvidenceRefResponse.from_domain(evidence_ref) for evidence_ref in fact.evidence],
        )


class ChatAnswerResponse(ApiModel):
    summary: str
    items: list[ChatAnswerItemResponse] = Field(default_factory=list)
