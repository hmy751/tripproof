from __future__ import annotations

from pydantic import Field

from server.answers.models import ChatAnswer, ChatAnswerItem
from server.extraction.models import EvidenceState
from server.schemas.base import ApiModel
from server.schemas.evidence import EvidenceRefResponse


class ChatAnswerItemResponse(ApiModel):
    id: str
    label: str
    body: str
    evidence_state: EvidenceState = Field(alias="evidenceState")
    value: str | None = None
    evidence: list[EvidenceRefResponse] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, item: ChatAnswerItem) -> "ChatAnswerItemResponse":
        return cls(
            id=item.id,
            label=item.label,
            body=item.body,
            evidence_state=item.evidence_state,
            value=item.value,
            evidence=[
                EvidenceRefResponse.from_domain(evidence) for evidence in item.evidence
            ],
        )


class ChatAnswerResponse(ApiModel):
    summary: str
    items: list[ChatAnswerItemResponse] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, answer: ChatAnswer) -> "ChatAnswerResponse":
        return cls(
            summary=answer.summary,
            items=[ChatAnswerItemResponse.from_domain(item) for item in answer.items],
        )
