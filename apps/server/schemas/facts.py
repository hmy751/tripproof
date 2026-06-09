from __future__ import annotations

from pydantic import Field

from server.extraction.models import EvidenceRef, EvidenceState, FactCandidate
from server.schemas.base import ApiModel


class EvidenceRefResponse(ApiModel):
    material_id: str = Field(alias="materialId")
    source_unit_id: str = Field(alias="sourceUnitId")
    label: str
    locator: str
    snippet: str

    @classmethod
    def from_domain(cls, evidence_ref: EvidenceRef) -> EvidenceRefResponse:
        return cls(
            material_id=evidence_ref.material_id,
            source_unit_id=evidence_ref.source_unit_id,
            label=evidence_ref.label,
            locator=evidence_ref.locator,
            snippet=evidence_ref.snippet,
        )


class FactCandidateResponse(ApiModel):
    id: str
    label: str
    value: str | None = None
    evidence_state: EvidenceState = Field(alias="evidenceState")
    evidence: list[EvidenceRefResponse]
    reason: str | None = None

    @classmethod
    def from_domain(cls, fact: FactCandidate) -> FactCandidateResponse:
        return cls(
            id=fact.id,
            label=fact.label,
            value=fact.value,
            evidence_state=fact.evidence_state,
            evidence=[EvidenceRefResponse.from_domain(evidence_ref) for evidence_ref in fact.evidence],
            reason=fact.reason,
        )
