from __future__ import annotations

from pydantic import Field

from server.extraction.models import EvidenceRef
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
