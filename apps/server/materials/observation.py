from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import uuid4

from server.retrieval.models import EmbeddingRecord, EmbeddingStatus
from server.runtime.config_snapshot import RuntimeConfigSnapshot
from server.schemas.materials import MaterialStatus

ObservationStepStatus = Literal["not_started", "succeeded", "failed"]
MaterialUploadStepName = Literal[
    "material_intake",
    "upload_snapshot",
    "content_extraction",
    "pdf_parse",
    "retrieval_preparation",
    "source_unit_build",
    "embedding_record_build",
    "retrieval_repository_upsert",
    "finalization",
    "material_status",
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

_STEP_ROOTS: tuple[MaterialUploadStepName, ...] = (
    "material_intake",
    "content_extraction",
    "retrieval_preparation",
    "finalization",
)
_STEP_CHILDREN: dict[MaterialUploadStepName, tuple[MaterialUploadStepName, ...]] = {
    "material_intake": ("upload_snapshot",),
    "content_extraction": ("pdf_parse",),
    "retrieval_preparation": (
        "source_unit_build",
        "embedding_record_build",
        "retrieval_repository_upsert",
    ),
    "finalization": ("material_status",),
}
_ALL_STEP_NAMES: tuple[MaterialUploadStepName, ...] = (
    "material_intake",
    "upload_snapshot",
    "content_extraction",
    "pdf_parse",
    "retrieval_preparation",
    "source_unit_build",
    "embedding_record_build",
    "retrieval_repository_upsert",
    "finalization",
    "material_status",
)
_ALLOWED_FACT_KEYS: dict[MaterialUploadStepName, set[str]] = {
    "material_intake": set(),
    "upload_snapshot": {"file_name", "content_type", "size_bytes", "size_limit_bytes"},
    "content_extraction": set(),
    "pdf_parse": {"page_count"},
    "retrieval_preparation": set(),
    "source_unit_build": {"count"},
    "embedding_record_build": {"count", "status_counts"},
    "retrieval_repository_upsert": {
        "executed",
        "source_unit_count",
        "embedding_record_count",
    },
    "finalization": set(),
    "material_status": {"status"},
}


@dataclass(frozen=True)
class MaterialUploadObservationStep:
    name: MaterialUploadStepName
    status: ObservationStepStatus
    facts: dict[str, ObservationFactValue] = field(default_factory=dict)
    failure_kind: MaterialUploadFailureKind | None = None
    children: list[MaterialUploadObservationStep] = field(default_factory=list)


@dataclass(frozen=True)
class MaterialUploadObservationRecord:
    id: str
    operation: Literal["material_upload"]
    material_id: str | None
    steps: list[MaterialUploadObservationStep]
    final_material_status: MaterialStatus | None
    failure_kind: MaterialUploadFailureKind | None
    runtime_config_snapshot: RuntimeConfigSnapshot | None = None

    def step(self, name: MaterialUploadStepName) -> MaterialUploadObservationStep:
        for step in self.steps:
            match = _find_step(step, name)
            if match is not None:
                return match
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
        runtime_config_snapshot: RuntimeConfigSnapshot | None = None,
    ) -> None:
        self._record_id = f"obs_mat_upload_{uuid4().hex[:12]}"
        self._material_id: str | None = None
        self._runtime_config_snapshot = runtime_config_snapshot
        self._steps = {
            step_name: MaterialUploadObservationStep(name=step_name, status="not_started")
            for step_name in _ALL_STEP_NAMES
        }
        self.succeed(
            "upload_snapshot",
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
        self.succeed("material_status", facts={"status": status})
        if failure_kind is not None:
            self._failure_kind = failure_kind

    def build(self) -> MaterialUploadObservationRecord:
        return MaterialUploadObservationRecord(
            id=self._record_id,
            operation="material_upload",
            material_id=self._material_id,
            steps=[self._build_step(step_name) for step_name in _STEP_ROOTS],
            final_material_status=self._final_material_status,
            failure_kind=self._failure_kind,
            runtime_config_snapshot=self._runtime_config_snapshot,
        )

    def _build_step(self, step_name: MaterialUploadStepName) -> MaterialUploadObservationStep:
        current = self._steps[step_name]
        children = [self._build_step(child_name) for child_name in _STEP_CHILDREN.get(step_name, ())]
        if not children:
            return current
        return MaterialUploadObservationStep(
            name=current.name,
            status=_derive_parent_status(children),
            facts=current.facts,
            failure_kind=_first_child_failure(children),
            children=children,
        )


class MaterialUploadObservationReporter:
    def __init__(
        self,
        *,
        sink: MaterialUploadObservationSink,
        file_name: str,
        content_type: str | None,
        size_bytes: int,
        size_limit_bytes: int,
        runtime_config_snapshot: RuntimeConfigSnapshot | None = None,
    ) -> None:
        self._sink = sink
        self._recorder = MaterialUploadObservationRecorder(
            file_name=file_name,
            content_type=content_type,
            size_bytes=size_bytes,
            size_limit_bytes=size_limit_bytes,
            runtime_config_snapshot=runtime_config_snapshot,
        )

    def upload_too_large(self) -> None:
        self._recorder.fail("upload_snapshot", "size_limit_exceeded")
        self._recorder.finalize("failed", failure_kind="size_limit_exceeded")

    def unsupported_file(self, *, material_id: str) -> None:
        self._recorder.fail("upload_snapshot", "unsupported_file")
        self._recorder.finalize(
            "failed",
            material_id=material_id,
            failure_kind="unsupported_file",
        )

    def pdf_parse_failed(self, *, material_id: str) -> None:
        self._recorder.fail("pdf_parse", "parse_failed")
        self._recorder.finalize(
            "failed",
            material_id=material_id,
            failure_kind="parse_failed",
        )

    def pdf_parsed(self, *, page_count: int) -> None:
        self._recorder.succeed("pdf_parse", facts={"page_count": page_count})

    def recorder_for_material_store(self) -> MaterialUploadObservationRecorder:
        return self._recorder

    def emit(self) -> None:
        emit_material_upload_observation(sink=self._sink, recorder=self._recorder)


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


def _derive_parent_status(children: list[MaterialUploadObservationStep]) -> ObservationStepStatus:
    if any(child.status == "failed" for child in children):
        return "failed"
    if any(child.status == "succeeded" for child in children):
        return "succeeded"
    return "not_started"


def _first_child_failure(
    children: list[MaterialUploadObservationStep],
) -> MaterialUploadFailureKind | None:
    for child in children:
        if child.failure_kind is not None:
            return child.failure_kind
        nested = _first_child_failure(child.children)
        if nested is not None:
            return nested
    return None


def _find_step(
    step: MaterialUploadObservationStep,
    name: MaterialUploadStepName,
) -> MaterialUploadObservationStep | None:
    if step.name == name:
        return step
    for child in step.children:
        match = _find_step(child, name)
        if match is not None:
            return match
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
