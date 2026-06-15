from __future__ import annotations

from pydantic import Field

from server.extraction.models import EvidenceState
from server.schemas.base import ApiModel
from server.schemas.facts import EvidenceRefResponse


class ChatAnswerItemResponse(ApiModel):
    id: str
    label: str
    body: str
    evidence_state: EvidenceState = Field(alias="evidenceState")
    value: str | None = None
    evidence: list[EvidenceRefResponse] = Field(default_factory=list)


class ChatAnswerResponse(ApiModel):
    summary: str
    items: list[ChatAnswerItemResponse] = Field(default_factory=list)
