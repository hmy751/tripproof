from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from server.materials.observation import (
    MaterialUploadObservationRecord,
    MaterialUploadObservationStep,
)
from server.observations.context import (
    ObservationRequestContext,
    current_observation_request_context,
    new_observation_request_context,
)
from server.observations.envelope import (
    OBSERVATION_EXPORT_SCHEMA_VERSION,
    ObservationExportEnvelope,
)
from server.observations.redaction import export_safe_facts
from server.questions.observation import (
    QuestionObservationRecord,
    QuestionObservationStep,
)
from server.runtime.config_snapshot import RuntimeConfigSnapshot


def material_upload_observation_export(
    record: MaterialUploadObservationRecord,
    *,
    exported_at: str | None = None,
    request_context: ObservationRequestContext | None = None,
) -> ObservationExportEnvelope:
    context = (
        request_context
        or current_observation_request_context()
        or new_observation_request_context()
    )
    return ObservationExportEnvelope(
        schema_version=OBSERVATION_EXPORT_SCHEMA_VERSION,
        exported_at=exported_at or _utc_timestamp(),
        operation=record.operation,
        record_id=record.id,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
        correlation_id_source=context.correlation_id_source,
        payload={
            "final_status": record.final_material_status,
            "failure_kind": record.failure_kind,
            "subject": {"material_id": record.material_id},
            "steps": [_material_step_to_payload(step) for step in record.steps],
            "runtime_config_snapshot": runtime_config_snapshot_to_payload(
                record.runtime_config_snapshot
            ),
        },
    )


def question_observation_export(
    record: QuestionObservationRecord,
    *,
    exported_at: str | None = None,
    request_context: ObservationRequestContext | None = None,
) -> ObservationExportEnvelope:
    context = (
        request_context
        or current_observation_request_context()
        or new_observation_request_context()
    )
    return ObservationExportEnvelope(
        schema_version=OBSERVATION_EXPORT_SCHEMA_VERSION,
        exported_at=exported_at or _utc_timestamp(),
        operation=record.operation,
        record_id=record.id,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
        correlation_id_source=context.correlation_id_source,
        payload={
            "final_status": record.final_question_status,
            "failure_kind": record.failure_kind,
            "subject": {},
            "steps": [_question_step_to_payload(step) for step in record.steps],
            "runtime_config_snapshot": runtime_config_snapshot_to_payload(
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
        "request_id": envelope.request_id,
        "correlation_id": envelope.correlation_id,
        "correlation_id_source": envelope.correlation_id_source,
        "payload": envelope.payload,
    }


def runtime_config_snapshot_to_payload(
    snapshot: RuntimeConfigSnapshot | None,
) -> dict[str, Any] | None:
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
            "seed": snapshot.answer_model.seed,
            "temperature": snapshot.answer_model.temperature,
        }

    relation_model = None
    if snapshot.relation_model is not None:
        relation_model = {
            "enabled": snapshot.relation_model.enabled,
            "mode": snapshot.relation_model.mode,
            "backend": snapshot.relation_model.backend,
            "model": snapshot.relation_model.model,
            "seed": snapshot.relation_model.seed,
            "temperature": snapshot.relation_model.temperature,
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
        "relation_model": relation_model,
    }


def _material_step_to_payload(step: MaterialUploadObservationStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "status": step.status,
        "failure_kind": step.failure_kind,
        "facts": export_safe_facts(step.name, step.facts),
        "children": [_material_step_to_payload(child) for child in step.children],
    }


def _question_step_to_payload(step: QuestionObservationStep) -> dict[str, Any]:
    return {
        "name": step.name,
        "status": step.status,
        "failure_kind": step.failure_kind,
        "facts": export_safe_facts(step.name, step.facts),
        "children": [_question_step_to_payload(child) for child in step.children],
    }


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
