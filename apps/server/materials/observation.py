from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import uuid4

from server.retrieval.models import EmbeddingRecord, EmbeddingStatus
from server.schemas.materials import MaterialStatus

ObservationStepStatus = Literal["not_started", "succeeded", "failed"]
MaterialUploadStepName = Literal[
    "upload",
    "pdf_parse",
    "source_unit_build",
    "embedding_record_build",
    "retrieval_repository_upsert",
]
MaterialUploadFailureKind = Literal[
    "unsupported_file",
    "parse_failed",
    "size_limit_exceeded",
    "source_unit_build_failed",
    "embedding_record_build_failed",
    "repository_upsert_failed",
]
ObservationFactValue = str | int | float | bool | None | dict[str, int]

_STEP_ORDER: tuple[MaterialUploadStepName, ...] = (
    "upload",
    "pdf_parse",
    "source_unit_build",
    "embedding_record_build",
    "retrieval_repository_upsert",
)
_ALLOWED_FACT_KEYS: dict[MaterialUploadStepName, set[str]] = {
    "upload": {"file_name", "content_type", "size_bytes", "size_limit_bytes"},
    "pdf_parse": {"page_count"},
    "source_unit_build": {"count"},
    "embedding_record_build": {"count", "status_counts"},
    "retrieval_repository_upsert": set(),
}


@dataclass(frozen=True)
class MaterialUploadObservationStep:
    name: MaterialUploadStepName
    status: ObservationStepStatus
    facts: dict[str, ObservationFactValue] = field(default_factory=dict)
    failure_kind: MaterialUploadFailureKind | None = None


@dataclass(frozen=True)
class MaterialUploadObservationRecord:
    id: str
    operation: Literal["material_upload"]
    material_id: str | None
    steps: list[MaterialUploadObservationStep]
    final_material_status: MaterialStatus | None
    failure_kind: MaterialUploadFailureKind | None

    def step(self, name: MaterialUploadStepName) -> MaterialUploadObservationStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(name)


class MaterialUploadObservationSink(Protocol):
    def record_material_upload(self, record: MaterialUploadObservationRecord) -> None:
        raise NotImplementedError


class NoopMaterialUploadObservationSink:
    def record_material_upload(self, record: MaterialUploadObservationRecord) -> None:
        return None


class InMemoryMaterialUploadObservationSink:
    def __init__(self) -> None:
        self._records: list[MaterialUploadObservationRecord] = []

    @property
    def records(self) -> list[MaterialUploadObservationRecord]:
        return list(self._records)

    def record_material_upload(self, record: MaterialUploadObservationRecord) -> None:
        self._records.append(record)


class MaterialUploadObservationRecorder:
    def __init__(
        self,
        *,
        file_name: str,
        content_type: str | None,
        size_bytes: int,
        size_limit_bytes: int,
    ) -> None:
        self._record_id = f"obs_mat_upload_{uuid4().hex[:12]}"
        self._material_id: str | None = None
        self._steps = {
            step_name: MaterialUploadObservationStep(name=step_name, status="not_started")
            for step_name in _STEP_ORDER
        }
        self.succeed(
            "upload",
            facts={
                "file_name": file_name,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "size_limit_bytes": size_limit_bytes,
            },
        )
        self._final_material_status: MaterialStatus | None = None
        self._failure_kind: MaterialUploadFailureKind | None = None

    def assign_material_id(self, material_id: str) -> None:
        self._material_id = material_id

    def succeed(
        self,
        step_name: MaterialUploadStepName,
        *,
        facts: dict[str, ObservationFactValue] | None = None,
    ) -> None:
        safe_facts = _merge_safe_facts(step_name, self._steps[step_name].facts, facts or {})
        self._steps[step_name] = MaterialUploadObservationStep(
            name=step_name,
            status="succeeded",
            facts=safe_facts,
        )

    def fail(
        self,
        step_name: MaterialUploadStepName,
        failure_kind: MaterialUploadFailureKind,
        *,
        facts: dict[str, ObservationFactValue] | None = None,
    ) -> None:
        safe_facts = _merge_safe_facts(step_name, self._steps[step_name].facts, facts or {})
        self._steps[step_name] = MaterialUploadObservationStep(
            name=step_name,
            status="failed",
            facts=safe_facts,
            failure_kind=failure_kind,
        )
        self._failure_kind = failure_kind

    def finalize(
        self,
        status: MaterialStatus,
        *,
        material_id: str | None = None,
        failure_kind: MaterialUploadFailureKind | None = None,
    ) -> None:
        if material_id is not None:
            self.assign_material_id(material_id)
        self._final_material_status = status
        if failure_kind is not None:
            self._failure_kind = failure_kind

    def build(self) -> MaterialUploadObservationRecord:
        return MaterialUploadObservationRecord(
            id=self._record_id,
            operation="material_upload",
            material_id=self._material_id,
            steps=[self._steps[step_name] for step_name in _STEP_ORDER],
            final_material_status=self._final_material_status,
            failure_kind=self._failure_kind,
        )


def embedding_record_build_facts(records: list[EmbeddingRecord]) -> dict[str, ObservationFactValue]:
    status_counts: dict[EmbeddingStatus, int] = dict(Counter(record.status for record in records))
    return {
        "count": len(records),
        "status_counts": status_counts,
    }


def emit_material_upload_observation(
    *,
    sink: MaterialUploadObservationSink,
    recorder: MaterialUploadObservationRecorder,
) -> None:
    try:
        sink.record_material_upload(recorder.build())
    except Exception:
        return None


def _safe_facts(
    step_name: MaterialUploadStepName,
    facts: dict[str, ObservationFactValue],
) -> dict[str, ObservationFactValue]:
    allowed_keys = _ALLOWED_FACT_KEYS[step_name]
    return {
        key: value
        for key, value in facts.items()
        if key in allowed_keys and _is_safe_fact_value(value)
    }


def _merge_safe_facts(
    step_name: MaterialUploadStepName,
    current: dict[str, ObservationFactValue],
    updates: dict[str, ObservationFactValue],
) -> dict[str, ObservationFactValue]:
    return {
        **_safe_facts(step_name, current),
        **_safe_facts(step_name, updates),
    }


def _is_safe_fact_value(value: ObservationFactValue) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, dict):
        return all(isinstance(key, str) and isinstance(item, int) for key, item in value.items())
    return False
