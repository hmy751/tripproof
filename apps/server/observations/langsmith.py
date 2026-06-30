from __future__ import annotations

from typing import Any, Protocol

from server.observations.export import ObservationExportEnvelope

_RUN_NAMES = {
    "material_upload": "tripproof.material_upload",
    "question_answer": "tripproof.question_answer",
}
_LOCAL_RICH_FACT_KEYS = {"candidates", "context_blocks", "items"}


class LangSmithRunWriter(Protocol):
    def write_run(
        self,
        *,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: dict[str, Any],
        events: list[dict[str, Any]],
        child_runs: list[dict[str, Any]],
        tags: list[str],
    ) -> None:
        raise NotImplementedError


class LangSmithRunTreeWriter:
    def __init__(self, *, project_name: str | None = None) -> None:
        self._project_name = project_name.strip() if project_name is not None else None

    def write_run(
        self,
        *,
        name: str,
        run_type: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: dict[str, Any],
        events: list[dict[str, Any]],
        child_runs: list[dict[str, Any]],
        tags: list[str],
    ) -> None:
        from langsmith.run_trees import RunTree

        kwargs: dict[str, Any] = {
            "name": name,
            "run_type": run_type,
            "inputs": inputs,
            "tags": tags,
        }
        if self._project_name:
            kwargs["project_name"] = self._project_name

        run = RunTree(**kwargs)
        _create_child_run_tree(run, child_runs)
        run.extra = {"metadata": metadata}
        if events:
            run.add_event(events)
        run.end(outputs=outputs)
        run.post(exclude_child_runs=False)


class LangSmithObservationExporter:
    def __init__(self, run_writer: LangSmithRunWriter) -> None:
        self._run_writer = run_writer

    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        try:
            payload = langsmith_run_payload(envelope)
            self._run_writer.write_run(**payload)
        except Exception:
            return None


def langsmith_run_payload(envelope: ObservationExportEnvelope) -> dict[str, Any]:
    payload = envelope.payload
    subject = _dict_payload(payload.get("subject"))
    runtime_config_snapshot = _dict_payload(payload.get("runtime_config_snapshot"))
    final_status = payload.get("final_status")
    failure_kind = payload.get("failure_kind")
    steps = _summary_steps(_list_payload(payload.get("steps")))

    metadata: dict[str, Any] = {
        "tripproof.schema_version": envelope.schema_version,
        "tripproof.operation": envelope.operation,
        "tripproof.record_id": envelope.record_id,
        "tripproof.request_id": envelope.request_id,
        "tripproof.correlation_id": envelope.correlation_id,
        "tripproof.correlation_id_source": envelope.correlation_id_source,
        "tripproof.exported_at": envelope.exported_at,
        "tripproof.final_status": final_status,
        "tripproof.failure_kind": failure_kind,
        "tripproof.subject": subject,
        "tripproof.runtime_config_snapshot": runtime_config_snapshot,
        "tripproof.step_statuses": _step_statuses(steps),
    }
    metadata.update(_flat_runtime_metadata(runtime_config_snapshot))

    return {
        "name": _RUN_NAMES[envelope.operation],
        "run_type": "chain",
        "inputs": {
            "operation": envelope.operation,
            "subject": subject,
        },
        "outputs": {
            "final_status": final_status,
            "failure_kind": failure_kind,
        },
        "metadata": metadata,
        "events": _step_events(steps, exported_at=envelope.exported_at),
        "child_runs": _step_child_runs(
            steps,
            runtime_config_snapshot=runtime_config_snapshot,
        ),
        "tags": [
            "tripproof",
            "tripproof.observation_export",
            f"tripproof.operation:{envelope.operation}",
            f"tripproof.correlation:{envelope.correlation_id}",
        ],
    }


def _step_child_runs(
    steps: list[dict[str, Any]],
    *,
    runtime_config_snapshot: dict[str, Any],
    parent_name: str | None = None,
    parent_path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    child_runs: list[dict[str, Any]] = []
    for step in steps:
        name = _string_value(step.get("name"))
        if name is None:
            continue
        path = (*parent_path, name)
        children = _list_payload(step.get("children"))
        kind = "parent_step" if children else "leaf_step"
        facts = _dict_payload(step.get("facts"))
        metadata = {
            "tripproof.synthetic_observation_step": True,
            "tripproof.step.kind": kind,
            "tripproof.step.name": name,
            "tripproof.step.path": ".".join(path),
            "tripproof.step.status": step.get("status"),
            "tripproof.step.failure_kind": step.get("failure_kind"),
            "tripproof.step.facts": facts,
        }
        metadata.update(_step_runtime_hint_metadata(name, runtime_config_snapshot))
        child_runs.append(
            {
                "name": name,
                "run_type": "chain",
                "inputs": {
                    "kind": kind,
                    "name": name,
                    "path": ".".join(path),
                    "parent_name": parent_name,
                },
                "outputs": {
                    "status": step.get("status"),
                    "failure_kind": step.get("failure_kind"),
                    "facts": facts,
                },
                "metadata": metadata,
                "children": _step_child_runs(
                    children,
                    runtime_config_snapshot=runtime_config_snapshot,
                    parent_name=name,
                    parent_path=path,
                ),
            }
        )
    return child_runs


def _summary_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_steps: list[dict[str, Any]] = []
    for step in steps:
        summary_step = dict(step)
        summary_step["facts"] = _summary_facts(_dict_payload(step.get("facts")))
        summary_step["children"] = _summary_steps(_list_payload(step.get("children")))
        summary_steps.append(summary_step)
    return summary_steps


def _summary_facts(facts: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in facts.items() if key not in _LOCAL_RICH_FACT_KEYS
    }


def _create_child_run_tree(parent: Any, child_runs: list[dict[str, Any]]) -> None:
    for child in child_runs:
        run = parent.create_child(
            name=child["name"],
            run_type=child["run_type"],
            inputs=child["inputs"],
            outputs=child["outputs"],
            extra={"metadata": child["metadata"]},
        )
        run.extra = {"metadata": child["metadata"]}
        run.end(outputs=child["outputs"])
        _create_child_run_tree(run, _list_payload(child.get("children")))


def _step_events(
    steps: list[dict[str, Any]],
    *,
    exported_at: str,
    parent_name: str | None = None,
    parent_path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for step in steps:
        name = _string_value(step.get("name"))
        if name is None:
            continue
        path = (*parent_path, name)
        children = _list_payload(step.get("children"))
        if children:
            events.append(
                {
                    "name": "tripproof.parent_step",
                    "time": exported_at,
                    "kwargs": {
                        "kind": "parent_step",
                        "name": name,
                        "path": ".".join(path),
                        "status": step.get("status"),
                        "failure_kind": step.get("failure_kind"),
                        "child_step_names": [
                            child["name"]
                            for child in children
                            if isinstance(child, dict)
                            and isinstance(child.get("name"), str)
                        ],
                    },
                }
            )
            events.extend(
                _step_events(
                    children,
                    exported_at=exported_at,
                    parent_name=name,
                    parent_path=path,
                )
            )
            continue

        events.append(
            {
                "name": "tripproof.leaf_step",
                "time": exported_at,
                "kwargs": {
                    "kind": "leaf_step",
                    "name": name,
                    "path": ".".join(path),
                    "parent_name": parent_name,
                    "status": step.get("status"),
                    "failure_kind": step.get("failure_kind"),
                    "facts": _dict_payload(step.get("facts")),
                },
            }
        )
    return events


def _step_statuses(
    steps: list[dict[str, Any]],
    *,
    parent_path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for step in steps:
        name = _string_value(step.get("name"))
        if name is None:
            continue
        path = (*parent_path, name)
        statuses.append(
            {
                "name": name,
                "path": ".".join(path),
                "status": step.get("status"),
                "failure_kind": step.get("failure_kind"),
            }
        )
        statuses.extend(
            _step_statuses(_list_payload(step.get("children")), parent_path=path)
        )
    return statuses


def _flat_runtime_metadata(snapshot: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    retrieval = _dict_payload(snapshot.get("retrieval"))
    embedding = _dict_payload(snapshot.get("embedding"))
    prompt = _dict_payload(snapshot.get("prompt"))
    answer_model = _dict_payload(snapshot.get("answer_model"))
    relation_model = _dict_payload(snapshot.get("relation_model"))

    _set_if_present(metadata, "tripproof.retrieval_backend", retrieval.get("backend"))
    _set_if_present(metadata, "tripproof.retrieval_top_k", retrieval.get("top_k"))
    _set_if_present(
        metadata,
        "tripproof.retrieval_similarity_threshold",
        retrieval.get("similarity_threshold"),
    )
    _set_if_present(metadata, "tripproof.embedding_provider", embedding.get("provider"))
    _set_if_present(metadata, "tripproof.embedding_model", embedding.get("model"))
    _set_if_present(
        metadata, "tripproof.embedding_dimensions", embedding.get("dimensions")
    )
    _set_if_present(metadata, "tripproof.prompt_name", prompt.get("name"))
    _set_if_present(metadata, "tripproof.prompt_version", prompt.get("version"))
    _set_if_present(metadata, "tripproof.prompt_body_hash", prompt.get("body_hash"))
    _set_if_present(
        metadata, "tripproof.answer_model_backend", answer_model.get("backend")
    )
    _set_if_present(metadata, "tripproof.answer_model", answer_model.get("model"))
    _set_if_present(metadata, "tripproof.answer_model_seed", answer_model.get("seed"))
    _set_if_present(
        metadata, "tripproof.answer_model_temperature", answer_model.get("temperature")
    )
    _set_if_present(
        metadata, "tripproof.relation_model_enabled", relation_model.get("enabled")
    )
    _set_if_present(
        metadata, "tripproof.relation_model_mode", relation_model.get("mode")
    )
    _set_if_present(
        metadata, "tripproof.relation_model_backend", relation_model.get("backend")
    )
    _set_if_present(metadata, "tripproof.relation_model", relation_model.get("model"))
    _set_if_present(
        metadata, "tripproof.relation_model_seed", relation_model.get("seed")
    )
    _set_if_present(
        metadata,
        "tripproof.relation_model_temperature",
        relation_model.get("temperature"),
    )
    return metadata


def _step_runtime_hint_metadata(
    step_name: str, snapshot: dict[str, Any]
) -> dict[str, Any]:
    hints = _runtime_hints_for_step(step_name, snapshot)
    if not hints:
        return {}
    metadata: dict[str, Any] = {"tripproof.step.runtime_hints": hints}
    for key, value in hints.items():
        metadata[f"tripproof.runtime_hint.{key}"] = value
    return metadata


def _runtime_hints_for_step(step_name: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    hints: dict[str, Any] = {}
    retrieval = _dict_payload(snapshot.get("retrieval"))
    embedding = _dict_payload(snapshot.get("embedding"))
    prompt = _dict_payload(snapshot.get("prompt"))
    answer_model = _dict_payload(snapshot.get("answer_model"))
    relation_model = _dict_payload(snapshot.get("relation_model"))

    if step_name in {
        "retrieval_preparation",
        "retrieval_repository_upsert",
        "material_scope",
        "retrieval_pipeline",
        "source_retrieval",
        "context_assembly",
        "candidate_summary",
    }:
        _copy_hint(hints, "retrieval_backend", retrieval.get("backend"))
        _copy_hint(hints, "retrieval_top_k", retrieval.get("top_k"))
        _copy_hint(
            hints,
            "retrieval_similarity_threshold",
            retrieval.get("similarity_threshold"),
        )

    if step_name in {
        "retrieval_preparation",
        "embedding_record_build",
        "source_retrieval",
    }:
        _copy_hint(hints, "embedding_auto_generate", embedding.get("auto_generate"))
        _copy_hint(hints, "embedding_provider", embedding.get("provider"))
        _copy_hint(hints, "embedding_model", embedding.get("model"))
        _copy_hint(hints, "embedding_dimensions", embedding.get("dimensions"))

    if step_name in {"answer_pipeline", "prompt_snapshot"}:
        _copy_hint(hints, "prompt_name", prompt.get("name"))
        _copy_hint(hints, "prompt_version", prompt.get("version"))
        _copy_hint(hints, "prompt_body_hash", prompt.get("body_hash"))

    if step_name in {"answer_pipeline", "composer_call"}:
        _copy_hint(hints, "answer_model_backend", answer_model.get("backend"))
        _copy_hint(hints, "answer_model", answer_model.get("model"))
        _copy_hint(hints, "relation_model_enabled", relation_model.get("enabled"))
        _copy_hint(hints, "relation_model_mode", relation_model.get("mode"))
        _copy_hint(hints, "relation_model_backend", relation_model.get("backend"))
        _copy_hint(hints, "relation_model", relation_model.get("model"))

    return hints


def _copy_hint(hints: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        hints[key] = value


def _set_if_present(metadata: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        metadata[key] = value


def _dict_payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_payload(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None
