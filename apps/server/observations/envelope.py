from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from server.observations.context import CorrelationIdSource

OBSERVATION_EXPORT_SCHEMA_VERSION = "tripproof.observation_export.v1"
ObservationExportOperation = Literal["material_upload", "question_answer"]


@dataclass(frozen=True)
class ObservationExportEnvelope:
    schema_version: str
    exported_at: str
    operation: ObservationExportOperation
    record_id: str
    request_id: str
    correlation_id: str
    correlation_id_source: CorrelationIdSource
    payload: dict[str, Any]
