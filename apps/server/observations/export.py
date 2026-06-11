from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal, Protocol

from server.materials.observation import (
    MaterialUploadObservationRecord,
    MaterialUploadObservationStep,
)
from server.questions.observation import QuestionObservationRecord, QuestionObservationStep
from server.runtime.config_snapshot import RuntimeConfigSnapshot


OBSERVATION_EXPORT_SCHEMA_VERSION = "tripproof.observation_export.v1"
ObservationExportOperation = Literal["material_upload", "question_answer"]


@dataclass(frozen=True)
class ObservationExportEnvelope:
    schema_version: str
    exported_at: str
    operation: ObservationExportOperation
    record_id: str
    payload: dict[str, Any]


class ObservationExporter(Protocol):
    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        raise NotImplementedError


class NoopObservationExporter:
    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        return None


class FanoutObservationExporter:
    def __init__(self, exporters: list[ObservationExporter]) -> None:
        self._exporters = list(exporters)

    @property
    def exporters(self) -> list[ObservationExporter]:
        return list(self._exporters)

    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        for exporter in self._exporters:
            try:
                exporter.export_observation(envelope)
            except Exception:
                continue


class LocalArtifactObservationExporter:
    def __init__(
        self,
        directory: str | Path,
        *,
        file_name: str = "observation-export.jsonl",
    ) -> None:
        self._path = Path(directory) / file_name

    @property
    def path(self) -> Path:
        return self._path

    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            observation_export_to_dict(envelope),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._path.open("a", encoding="utf-8") as export_file:
            export_file.write(f"{line}\n")


class MaterialUploadObservationExportSink:
    def __init__(self, exporter: ObservationExporter) -> None:
        self._exporter = exporter

    def record_material_upload(self, record: MaterialUploadObservationRecord) -> None:
        self._exporter.export_observation(material_upload_observation_export(record))


class QuestionObservationExportSink:
    def __init__(self, exporter: ObservationExporter) -> None:
        self._exporter = exporter

    def record_question_answer(self, record: QuestionObservationRecord) -> None:
        self._exporter.export_observation(question_observation_export(record))


def create_observation_exporter_from_directory(directory: str | Path | None) -> ObservationExporter:
    if directory is None or str(directory).strip() == "":
        return NoopObservationExporter()
    return LocalArtifactObservationExporter(directory)


def material_upload_observation_export(
    record: MaterialUploadObservationRecord,
    *,
    exported_at: str | None = None,
) -> ObservationExportEnvelope:
    return ObservationExportEnvelope(
        schema_version=OBSERVATION_EXPORT_SCHEMA_VERSION,
        exported_at=exported_at or _utc_timestamp(),
        operation=record.operation,
        record_id=record.id,
        payload={
            "final_status": record.final_material_status,
            "failure_kind": record.failure_kind,
            "subject": {"material_id": record.material_id},
            "steps": [_material_step_to_payload(step) for step in record.steps],
            "runtime_config_snapshot": _runtime_config_snapshot_to_payload(
                record.runtime_config_snapshot
            ),
        },
    )


def question_observation_export(
    record: QuestionObservationRecord,
    *,
    exported_at: str | None = None,
) -> ObservationExportEnvelope:
    return ObservationExportEnvelope(
        schema_version=OBSERVATION_EXPORT_SCHEMA_VERSION,
        exported_at=exported_at or _utc_timestamp(),
        operation=record.operation,
        record_id=record.id,
        payload={
            "final_status": record.final_question_status,
            "failure_kind": record.failure_kind,
            "subject": {},
            "steps": [_question_step_to_payload(step) for step in record.steps],
            "runtime_config_snapshot": _runtime_config_snapshot_to_payload(
                record.runtime_config_snapshot
            ),
        },
    )


def observation_export_to_dict(envelope: ObservationExportEnvelope) -> dict[str, Any]:
    return {
        "schema_version": envelope.schema_version,
        "exported_at": envelope.exported_at,
        "operation": envelope.operation,
        "record_id": envelope.record_id,
        "payload": envelope.payload,
    }


def _material_step_to_payload(step: MaterialUploadObservationStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "status": step.status,
        "failure_kind": step.failure_kind,
        "facts": _export_safe_facts(step.name, step.facts),
        "children": [_material_step_to_payload(child) for child in step.children],
    }


def _question_step_to_payload(step: QuestionObservationStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "status": step.status,
        "failure_kind": step.failure_kind,
        "facts": _export_safe_facts(step.name, step.facts),
        "children": [_question_step_to_payload(child) for child in step.children],
    }


def _export_safe_facts(step_name: str, facts: dict[str, Any]) -> dict[str, Any]:
    exported: dict[str, Any] = {}
    for key, value in facts.items():
        if step_name == "upload_snapshot" and key == "file_name":
            exported.update(_file_name_summary(value))
            continue
        if _is_export_safe_value(value):
            exported[key] = value
    return exported


def _file_name_summary(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or value == "":
        return {"file_name_present": False, "file_extension": None}
    suffix = Path(value).suffix.lower()
    return {
        "file_name_present": True,
        "file_extension": suffix[1:] if suffix else None,
    }


def _runtime_config_snapshot_to_payload(snapshot: RuntimeConfigSnapshot | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None

    prompt = None
    if snapshot.prompt is not None:
        prompt = {
            "domain": snapshot.prompt.domain,
            "name": snapshot.prompt.name,
            "version": snapshot.prompt.version,
            "body_hash": snapshot.prompt.body_hash,
            "file_hash": snapshot.prompt.file_hash,
            "asset_path": snapshot.prompt.asset_path,
        }

    answer_model = None
    if snapshot.answer_model is not None:
        answer_model = {
            "backend": snapshot.answer_model.backend,
            "model": snapshot.answer_model.model,
        }

    return {
        "retrieval": {
            "backend": snapshot.retrieval.backend,
            "top_k": snapshot.retrieval.top_k,
            "similarity_threshold": snapshot.retrieval.similarity_threshold,
        },
        "embedding": {
            "auto_generate": snapshot.embedding.auto_generate,
            "provider": snapshot.embedding.provider,
            "model": snapshot.embedding.model,
            "dimensions": snapshot.embedding.dimensions,
        },
        "prompt": prompt,
        "answer_model": answer_model,
    }


def _is_export_safe_value(value: Any) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_export_safe_value(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return all(_is_export_safe_value(item) for item in value)
    return False


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
