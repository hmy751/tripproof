from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Literal
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_PATH = REPO_ROOT / "apps"
if str(APPS_PATH) not in sys.path:
    sys.path.insert(0, str(APPS_PATH))

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfWriter  # noqa: E402
from pypdf.generic import (  # noqa: E402
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from html_report import DEFAULT_REPORT_FILE_NAME, write_html_report  # noqa: E402
from server.app import (  # noqa: E402
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    create_app,
)
from server.materials.store import MaterialStore  # noqa: E402
from server.observations.export import LocalArtifactObservationExporter  # noqa: E402
from server.retrieval.embeddings import EmbeddingProfile  # noqa: E402
from server.runtime.config_snapshot import (  # noqa: E402
    answer_model_runtime_config_snapshot_from_composer,
    relation_model_runtime_config_snapshot_from_composer,
)
from server.testing import (  # noqa: E402
    InMemoryRetrievalRepository,
    MissingLibraryChatAnswerComposer,
)

RUN_SCHEMA_VERSION = "tripproof.eval_run.question_dataset.v1"
RUN_PURPOSE_ORIGINAL_PDF_BASELINE = "original_pdf_baseline"
RUN_PURPOSE_SAMPLE_FIXTURE_SMOKE = "sample_fixture_smoke"
RUNTIME_MODE_PRODUCTION = "production"
RUNTIME_MODE_DETERMINISTIC = "deterministic"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "eval" / "runs" / "question-dataset"
DEFAULT_QUESTIONS_FILE = (
    REPO_ROOT / "eval" / "datasets" / "agoda-booking-confirmation" / "questions.json"
)
DEFAULT_MATERIAL_TEXT_FILE = (
    REPO_ROOT
    / "fixtures"
    / "accommodation-checkin"
    / "agoda-booking-confirmation-sample.txt"
)


@dataclass(frozen=True)
class MaterialInput:
    kind: Literal["pdf_file", "text_fixture_rendered_pdf"]
    source_path: Path
    display_name: str
    upload_file_name: str
    content: bytes
    content_type: str
    run_purpose: Literal["original_pdf_baseline", "sample_fixture_smoke"]


RuntimeMode = Literal["production", "deterministic"]


def main() -> int:
    args = _parse_args()
    if args.repeat < 1:
        raise ValueError("--repeat must be at least 1")

    if args.repeat == 1:
        artifact, artifact_path = run_question_dataset(
            output_dir=args.output_dir,
            questions_file=args.questions_file,
            material_text_file=args.material_text_file,
            material_pdf_file=args.material_pdf_file,
            run_id=args.run_id,
            correlation_prefix=args.correlation_prefix,
            question_limit=args.question_limit,
            runtime_mode=args.runtime_mode,
            answer_composer_backend=args.answer_composer_backend,
            answer_seed=args.answer_seed,
        )
        output = {**artifact, "artifact_path": str(artifact_path)}
    else:
        bundle, artifact_path = run_question_dataset_repeat(
            output_dir=args.output_dir,
            questions_file=args.questions_file,
            material_text_file=args.material_text_file,
            material_pdf_file=args.material_pdf_file,
            run_id=args.run_id,
            correlation_prefix=args.correlation_prefix,
            question_limit=args.question_limit,
            runtime_mode=args.runtime_mode,
            answer_composer_backend=args.answer_composer_backend,
            answer_seed=args.answer_seed,
            repeat_count=args.repeat,
        )
        output = {**bundle, "artifact_path": str(artifact_path)}

    if args.json:
        print(
            json.dumps(
                output,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"wrote {artifact_path}")
    return 0


def run_question_dataset_repeat(
    *,
    output_dir: Path,
    questions_file: Path,
    material_text_file: Path | None,
    material_pdf_file: Path | None = None,
    run_id: str | None = None,
    correlation_prefix: str | None = None,
    question_limit: int | None = None,
    runtime_mode: RuntimeMode = RUNTIME_MODE_PRODUCTION,
    answer_composer_backend: str | None = None,
    answer_seed: int | None = None,
    repeat_count: int,
) -> tuple[dict[str, Any], Path]:
    if repeat_count < 1:
        raise ValueError("repeat_count must be at least 1")

    group_id = _run_id(run_id)
    group_dir = output_dir / group_id
    group_dir.mkdir(parents=True, exist_ok=True)
    code_version = _code_version_artifact()
    runs: list[dict[str, Any]] = []
    for repeat_index in range(1, repeat_count + 1):
        repeat_suffix = f"r{repeat_index:02d}"
        repeat_run_id = _with_suffix(group_id, suffix=f"-{repeat_suffix}", limit=128)
        repeat_correlation_prefix = _repeat_correlation_prefix(
            correlation_prefix=correlation_prefix,
            run_group_id=group_id,
            repeat_suffix=repeat_suffix,
        )
        artifact, artifact_path = run_question_dataset(
            output_dir=output_dir,
            questions_file=questions_file,
            material_text_file=material_text_file,
            material_pdf_file=material_pdf_file,
            run_id=repeat_run_id,
            correlation_prefix=repeat_correlation_prefix,
            question_limit=question_limit,
            runtime_mode=runtime_mode,
            answer_composer_backend=answer_composer_backend,
            answer_seed=answer_seed,
            repeat_group_id=group_id,
            repeat_index=repeat_index,
            repeat_count=repeat_count,
            code_version=code_version,
        )
        runs.append(
            {
                "run_id": artifact["run_id"],
                "repeat_index": repeat_index,
                "artifact_path": _repo_relative(artifact_path),
                "html_report_path": _repo_relative(
                    artifact_path.parent / artifact["html_report"]["path"]
                ),
                "rule_pass_count": sum(
                    1
                    for question in artifact["question_results"]
                    if question.get("rule_check", {}).get("passed") is True
                ),
                "question_count": len(artifact["question_results"]),
            }
        )

    bundle = {
        "schema_version": "tripproof.eval_run.question_dataset_repeat.v1",
        "kind": "question_dataset_repeat",
        "run_group_id": group_id,
        "created_at": datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "repeat": {
            "count": repeat_count,
            "run_ids": [run["run_id"] for run in runs],
        },
        "code_version": code_version,
        "run_config": _run_config_artifact(
            questions_file=questions_file,
            material_text_file=material_text_file,
            material_pdf_file=material_pdf_file,
            question_limit=question_limit,
            runtime_mode=runtime_mode,
            answer_composer_backend=answer_composer_backend,
            answer_seed=answer_seed,
        ),
        "runs": runs,
        "interpretation_note": (
            "Repeat runs expose the current noise floor. A single rule pass count is "
            "not a product improvement proof."
        ),
    }
    artifact_path = group_dir / "repeat.json"
    artifact_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle, artifact_path


def run_question_dataset(
    *,
    output_dir: Path,
    questions_file: Path,
    material_text_file: Path | None,
    material_pdf_file: Path | None = None,
    run_id: str | None = None,
    correlation_prefix: str | None = None,
    question_limit: int | None = None,
    runtime_mode: RuntimeMode = RUNTIME_MODE_PRODUCTION,
    answer_composer_backend: str | None = None,
    answer_seed: int | None = None,
    repeat_group_id: str | None = None,
    repeat_index: int = 1,
    repeat_count: int = 1,
    code_version: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    active_run_id = _run_id(run_id)
    active_correlation_prefix = correlation_prefix or f"eval_{uuid4().hex[:8]}"
    run_dir = output_dir / active_run_id
    observation_dir = run_dir / "observations"
    observation_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / "run.json"

    questions = _load_questions(questions_file)
    if question_limit is not None:
        questions = questions[:question_limit]
    material_input = _material_input(
        material_text_file=material_text_file,
        material_pdf_file=material_pdf_file,
    )

    exporter = LocalArtifactObservationExporter(observation_dir)
    app = _create_dataset_app(
        runtime_mode=runtime_mode,
        answer_composer_backend=answer_composer_backend,
        answer_seed=answer_seed,
        observation_exporter=exporter,
    )
    client = TestClient(app)

    upload = client.post(
        "/api/materials",
        data={"displayName": material_input.display_name},
        files={
            "file": (
                material_input.upload_file_name,
                material_input.content,
                material_input.content_type,
            )
        },
    )
    material_body = _response_json(upload)
    if upload.status_code != 200:
        raise RuntimeError(
            f"material upload failed: {upload.status_code} {upload.text}"
        )
    material_id = _text(material_body.get("id"))
    if not material_id:
        raise RuntimeError("material upload did not return a material id")

    question_results: list[dict[str, Any]] = []
    used_correlation_ids: set[str] = set()
    product_trace_safe = _has_no_product_trace_ids(material_body)
    for question_index, question in enumerate(questions, start=1):
        question_id = _text(
            question.get("id"), fallback=f"question-{len(question_results) + 1}"
        )
        correlation_id = _unique_correlation_id(
            prefix=active_correlation_prefix,
            question_id=question_id,
            question_index=question_index,
            used_ids=used_correlation_ids,
        )
        response = client.post(
            "/api/questions",
            headers={CORRELATION_ID_HEADER: correlation_id},
            json={
                "question": _text(question.get("question")),
                "materialIds": [material_id],
            },
        )
        question_body = _response_json(response)
        product_trace_safe = product_trace_safe and _has_no_product_trace_ids(
            question_body
        )
        question_results.append(
            _question_result(
                question=question,
                correlation_id=correlation_id,
                response=response,
                question_body=question_body,
            )
        )

    observation_rows = _read_jsonl(exporter.path)
    artifact = _artifact(
        run_id=active_run_id,
        questions_file=questions_file,
        material_input=material_input,
        upload_response=upload,
        material=material_body,
        question_results=question_results,
        observation_export_path=Path("observations") / exporter.path.name,
        observation_rows=observation_rows,
        runtime=_runtime_artifact(app=app, runtime_mode=runtime_mode),
        run_config=_run_config_artifact(
            questions_file=questions_file,
            material_text_file=material_text_file,
            material_pdf_file=material_pdf_file,
            question_limit=question_limit,
            runtime_mode=runtime_mode,
            answer_composer_backend=answer_composer_backend,
            answer_seed=answer_seed,
        ),
        repeat={
            "group_id": repeat_group_id or active_run_id,
            "index": repeat_index,
            "count": repeat_count,
        },
        code_version=code_version or _code_version_artifact(),
        product_trace_safe=product_trace_safe,
    )
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_html_report(run_json_path=artifact_path)
    return artifact, artifact_path


def _artifact(
    *,
    run_id: str,
    questions_file: Path,
    material_input: MaterialInput,
    upload_response,
    material: dict[str, Any],
    question_results: list[dict[str, Any]],
    observation_export_path: Path,
    observation_rows: list[dict[str, Any]],
    runtime: dict[str, Any],
    run_config: dict[str, Any],
    repeat: dict[str, Any],
    code_version: dict[str, Any],
    product_trace_safe: bool,
) -> dict[str, Any]:
    upload_request_id = upload_response.headers.get(REQUEST_ID_HEADER, "")
    upload_correlation_id = upload_response.headers.get(CORRELATION_ID_HEADER, "")
    question_correlation_ids = [
        _text(question.get("correlation_id")) for question in question_results
    ]
    question_correlation_counts = Counter(question_correlation_ids)
    exported_question_correlation_counts = Counter(
        _text(row.get("correlation_id"))
        for row in observation_rows
        if row.get("operation") == "question_answer"
    )
    checks = {
        "upload_response_had_request_id": upload_request_id.startswith("req_"),
        "upload_request_fell_back_to_own_correlation_id": upload_correlation_id
        == upload_request_id,
        "upload_status_code_ok": upload_response.status_code == 200,
        "all_question_responses_had_request_id": all(
            _text(question.get("request_id")).startswith("req_")
            for question in question_results
        ),
        "all_question_responses_correlation_matched_input": all(
            question.get("correlation_id") == question.get("response_correlation_id")
            for question in question_results
        ),
        "generated_question_correlation_ids_unique": len(question_correlation_ids)
        == len(question_correlation_counts),
        "all_question_exports_correlation_matched_inputs": all(
            exported_question_correlation_counts[correlation_id] >= count
            for correlation_id, count in question_correlation_counts.items()
        ),
        "product_json_has_no_request_or_correlation_id": product_trace_safe,
        "run_purpose_matches_material_input": _run_purpose_matches_material_input(
            material_input
        ),
    }
    dataset: dict[str, Any] = {
        "questions_file": _repo_relative(questions_file),
        "question_count": len(question_results),
        "material_input": {
            "kind": material_input.kind,
            "source_path": _repo_relative(material_input.source_path),
            "uploaded_file_name": material_input.upload_file_name,
        },
    }
    if material_input.kind == "pdf_file":
        dataset["material_pdf_file"] = _repo_relative(material_input.source_path)
    else:
        dataset["material_text_file"] = _repo_relative(material_input.source_path)

    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "kind": "question_dataset",
        "run_purpose": {
            "id": material_input.run_purpose,
            "label": _run_purpose_label(material_input.run_purpose),
            "agoda_original_pdf_baseline": material_input.run_purpose
            == RUN_PURPOSE_ORIGINAL_PDF_BASELINE,
            "sample_fixture_smoke": material_input.run_purpose
            == RUN_PURPOSE_SAMPLE_FIXTURE_SMOKE,
        },
        "dataset": dataset,
        "product_entry_point": {
            "type": "fastapi_test_client",
            "endpoints": ["POST /api/materials", "POST /api/questions"],
        },
        "code_version": code_version,
        "run_config": run_config,
        "repeat": repeat,
        "runtime": runtime,
        "requests": {
            "material_upload": {
                "status_code": upload_response.status_code,
                "request_id": upload_request_id,
                "correlation_id": upload_correlation_id,
                "material_id": material.get("id"),
                "material_status": material.get("status"),
            }
        },
        "question_results": question_results,
        "observation_export": {
            "path": str(observation_export_path),
            "record_count": len(observation_rows),
            "records": [_observation_summary(row) for row in observation_rows],
        },
        "html_report": {"path": DEFAULT_REPORT_FILE_NAME},
        "checks": checks,
        "next_verification_point": (
            "Open report.html, pick a failed question, and follow the observation "
            "source path for the same correlation_id."
        ),
    }


def _create_dataset_app(
    *,
    runtime_mode: RuntimeMode,
    answer_composer_backend: str | None,
    answer_seed: int | None,
    observation_exporter: LocalArtifactObservationExporter,
):
    if runtime_mode == RUNTIME_MODE_DETERMINISTIC:
        store = MaterialStore(
            embedding_provider=DatasetEmbeddingProvider(),
            embedding_auto_generate=True,
            retrieval_repository=InMemoryRetrievalRepository(),
            retrieval_backend="memory",
        )
        composer = (
            None
            if answer_composer_backend == "ollama"
            else MissingLibraryChatAnswerComposer()
        )
        if composer is None and answer_seed is not None:
            from server.answers.library_chat import (
                create_library_chat_answer_composer_from_config,
            )

            composer = create_library_chat_answer_composer_from_config(
                answer_seed=answer_seed
            )
        return create_app(
            store=store,
            library_chat_answer_composer=composer,
            observation_exporter=observation_exporter,
        )

    if runtime_mode != RUNTIME_MODE_PRODUCTION:
        raise ValueError(f"Unsupported runtime mode: {runtime_mode}")

    composer = (
        MissingLibraryChatAnswerComposer()
        if answer_composer_backend in ("missing", "disabled")
        else None
    )
    if composer is None and answer_seed is not None:
        from server.answers.library_chat import (
            create_library_chat_answer_composer_from_config,
        )

        composer = create_library_chat_answer_composer_from_config(
            answer_seed=answer_seed
        )
    return create_app(
        library_chat_answer_composer=composer,
        observation_exporter=observation_exporter,
    )


def _runtime_artifact(*, app, runtime_mode: RuntimeMode) -> dict[str, Any]:
    settings = app.state.runtime_config_settings
    answer_model = answer_model_runtime_config_snapshot_from_composer(
        app.state.library_chat_answer_composer
    )
    relation_model = relation_model_runtime_config_snapshot_from_composer(
        app.state.library_chat_answer_composer
    )
    answer_composer = answer_model.backend if answer_model is not None else "unknown"
    answer_model_name = answer_model.model if answer_model is not None else None
    answer_seed = answer_model.seed if answer_model is not None else None
    answer_temperature = answer_model.temperature if answer_model is not None else None
    relation_enabled = relation_model.enabled if relation_model is not None else None
    relation_mode = relation_model.mode if relation_model is not None else None
    relation_backend = relation_model.backend if relation_model is not None else None
    relation_model_name = relation_model.model if relation_model is not None else None
    relation_seed = relation_model.seed if relation_model is not None else None
    relation_temperature = (
        relation_model.temperature if relation_model is not None else None
    )
    return {
        "mode": runtime_mode,
        "production_like": runtime_mode == RUNTIME_MODE_PRODUCTION,
        "retrieval_backend": settings.retrieval_backend,
        "retrieval_top_k": settings.retrieval_top_k,
        "retrieval_similarity_threshold": settings.retrieval_similarity_threshold,
        "embedding_auto_generate": settings.embedding_auto_generate,
        "embedding_provider": settings.embedding_profile.provider,
        "embedding_model": settings.embedding_profile.model,
        "embedding_dimensions": settings.embedding_profile.dimensions,
        "answer_composer": answer_composer,
        "answer_model": answer_model_name,
        "answer_seed": answer_seed,
        "answer_seed_specified": answer_seed is not None,
        "answer_temperature": answer_temperature,
        "relation_extractor_enabled": relation_enabled,
        "relation_extractor_mode": relation_mode,
        "relation_model_backend": relation_backend,
        "relation_model": relation_model_name,
        "relation_seed": relation_seed,
        "relation_temperature": relation_temperature,
    }


def _question_result(
    *,
    question: dict[str, Any],
    correlation_id: str,
    response,
    question_body: dict[str, Any],
) -> dict[str, Any]:
    answer = _dict(question_body.get("answer"))
    answer_items = _list(answer.get("items"))
    evidence_state_counts = Counter(
        item.get("evidenceState")
        for item in answer_items
        if isinstance(item, dict) and isinstance(item.get("evidenceState"), str)
    )
    expected_state = _text(question.get("expected_evidence_state"))
    required_cues = _string_list(question.get("required_evidence_cues"))
    must_not_claim = _string_list(question.get("must_not_claim"))
    text_for_rules = _answer_text_for_rules(answer.get("summary"), answer_items)
    missing_cues = [cue for cue in required_cues if cue not in text_for_rules]
    must_not_hits = [claim for claim in must_not_claim if claim in text_for_rules]
    state_matched = (
        evidence_state_counts.get(expected_state, 0) > 0 if expected_state else False
    )
    return {
        "id": _text(question.get("id"), fallback="question"),
        "priority": _text(question.get("priority"), fallback="not_recorded"),
        "type": _text(question.get("type"), fallback="not_recorded"),
        "question": _text(question.get("question")),
        "correlation_id": correlation_id,
        "request_id": response.headers.get(REQUEST_ID_HEADER, ""),
        "response_correlation_id": response.headers.get(CORRELATION_ID_HEADER, ""),
        "status_code": response.status_code,
        "expected": {
            "evidence_state": expected_state,
            "answer_pattern": _text(question.get("expected_answer_pattern")),
            "required_evidence_cues": required_cues,
            "must_not_claim": must_not_claim,
            "metrics": _string_list(question.get("metrics")),
        },
        "observed": {
            "status": question_body.get("status"),
            "answer_summary": answer.get("summary"),
            "answer_items": _answer_item_summaries(answer_items),
            "item_count": len(answer_items),
            "evidence_state_counts": dict(evidence_state_counts),
        },
        "rule_check": {
            "passed": response.status_code == 200
            and state_matched
            and not missing_cues
            and not must_not_hits,
            "state_matched": state_matched,
            "missing_cues": missing_cues,
            "must_not_hits": must_not_hits,
        },
    }


def _load_questions(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError("questions file must contain a JSON array")
    questions = [item for item in value if isinstance(item, dict)]
    if not questions:
        raise ValueError("questions file did not contain any question objects")
    return questions


def _run_id(value: str | None) -> str:
    if value is not None:
        slug = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", slug):
            raise ValueError(
                "run_id must be 1-128 characters of A-Z, a-z, 0-9, '.', '_', ':', or '-'."
            )
        return slug
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _material_input(
    *,
    material_text_file: Path | None,
    material_pdf_file: Path | None,
) -> MaterialInput:
    if material_text_file is not None and material_pdf_file is not None:
        raise ValueError(
            "--material-text-file and --material-pdf-file are mutually exclusive"
        )

    if material_pdf_file is not None:
        path = material_pdf_file
        return MaterialInput(
            kind="pdf_file",
            source_path=path,
            display_name=path.stem,
            upload_file_name=path.name,
            content=path.read_bytes(),
            content_type="application/pdf",
            run_purpose=RUN_PURPOSE_ORIGINAL_PDF_BASELINE,
        )

    path = material_text_file or DEFAULT_MATERIAL_TEXT_FILE
    material_text = path.read_text(encoding="utf-8")
    return MaterialInput(
        kind="text_fixture_rendered_pdf",
        source_path=path,
        display_name=path.stem,
        upload_file_name=f"{path.stem}.pdf",
        content=_pdf_with_text(material_text),
        content_type="application/pdf",
        run_purpose=RUN_PURPOSE_SAMPLE_FIXTURE_SMOKE,
    )


def _run_purpose_matches_material_input(material_input: MaterialInput) -> bool:
    return (
        material_input.kind == "pdf_file"
        and material_input.run_purpose == RUN_PURPOSE_ORIGINAL_PDF_BASELINE
    ) or (
        material_input.kind == "text_fixture_rendered_pdf"
        and material_input.run_purpose == RUN_PURPOSE_SAMPLE_FIXTURE_SMOKE
    )


def _run_purpose_label(run_purpose: str) -> str:
    if run_purpose == RUN_PURPOSE_ORIGINAL_PDF_BASELINE:
        return "Original PDF baseline"
    if run_purpose == RUN_PURPOSE_SAMPLE_FIXTURE_SMOKE:
        return "Sample fixture smoke"
    return run_purpose


def _pdf_with_text(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("utf-8"))
    page[NameObject("/Contents")] = stream
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _answer_text_for_rules(summary: object, answer_items: object) -> str:
    parts: list[str] = []
    if isinstance(summary, str):
        parts.append(summary)
    if isinstance(answer_items, list):
        for item in answer_items:
            if not isinstance(item, dict):
                continue
            body = item.get("body")
            if isinstance(body, str):
                parts.append(body)
            evidence = item.get("evidence")
            if not isinstance(evidence, list):
                continue
            for ref in evidence:
                if isinstance(ref, dict) and isinstance(ref.get("snippet"), str):
                    parts.append(ref["snippet"])
    return "\n".join(parts)


def _answer_item_summaries(answer_items: object) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    if not isinstance(answer_items, list):
        return summaries
    for item in answer_items:
        if not isinstance(item, dict):
            continue
        summaries.append(
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "body": item.get("body"),
                "value": item.get("value"),
                "evidence_state": item.get("evidenceState"),
                "evidence": _evidence_summaries(item.get("evidence")),
            }
        )
    return summaries


def _evidence_summaries(evidence_items: object) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    if not isinstance(evidence_items, list):
        return summaries
    for evidence in evidence_items:
        if not isinstance(evidence, dict):
            continue
        summaries.append(
            {
                "material_id": evidence.get("materialId"),
                "source_unit_id": evidence.get("sourceUnitId"),
                "label": evidence.get("label"),
                "locator": evidence.get("locator"),
                "snippet": evidence.get("snippet"),
            }
        )
    return summaries


def _has_no_product_trace_ids(payload: object) -> bool:
    if isinstance(payload, dict):
        return not any(
            key in payload
            for key in ("requestId", "correlationId", "request_id", "correlation_id")
        )
    return True


def _response_json(response) -> dict[str, Any]:
    try:
        value = response.json()
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _observation_summary(row: dict[str, Any]) -> dict[str, Any]:
    payload = _dict(row.get("payload"))
    return {
        "operation": row.get("operation"),
        "request_id": row.get("request_id"),
        "correlation_id": row.get("correlation_id"),
        "final_status": payload.get("final_status"),
        "failure_kind": payload.get("failure_kind"),
    }


def _correlation_id(*, prefix: str, question_id: str) -> str:
    value = f"{prefix}_{question_id}"
    return re.sub(r"[^A-Za-z0-9._:-]", "_", value)[:128] or f"eval_{uuid4().hex[:8]}"


def _unique_correlation_id(
    *,
    prefix: str,
    question_id: str,
    question_index: int,
    used_ids: set[str],
) -> str:
    base = _correlation_id(prefix=prefix, question_id=question_id)
    candidate = base
    collision_count = 1
    while candidate in used_ids:
        suffix = f"_{question_index}_{collision_count}"
        candidate = _with_suffix(base, suffix=suffix, limit=128)
        collision_count += 1
    used_ids.add(candidate)
    return candidate


def _with_suffix(value: str, *, suffix: str, limit: int) -> str:
    if len(suffix) >= limit:
        return suffix[-limit:]
    return f"{value[: limit - len(suffix)]}{suffix}"


def _repeat_correlation_prefix(
    *, correlation_prefix: str | None, run_group_id: str, repeat_suffix: str
) -> str:
    base = correlation_prefix or f"eval_{run_group_id}"
    return _with_suffix(base, suffix=f"_{repeat_suffix}", limit=80)


def _code_version_artifact() -> dict[str, Any]:
    commit_hash = _git_output("rev-parse", "--verify", "HEAD")
    branch = _git_output("rev-parse", "--abbrev-ref", "HEAD")
    status = _git_status_porcelain()
    tracked_diff = _git_output_allow_empty("diff", "HEAD", "--")
    untracked = _git_output_allow_empty("ls-files", "--others", "--exclude-standard")
    return {
        "vcs": "git",
        "commit_hash": commit_hash,
        "branch": branch,
        "dirty": bool(status),
        "tracked_diff_hash": _sha256_or_none(tracked_diff),
        "untracked_file_count": len(untracked.splitlines()) if untracked else 0,
        "status_available": status is not None,
    }


def _git_output(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    output = result.stdout.strip()
    return output or None


def _git_output_allow_empty(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout


def _git_status_porcelain() -> str | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _sha256_or_none(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _run_config_artifact(
    *,
    questions_file: Path,
    material_text_file: Path | None,
    material_pdf_file: Path | None,
    question_limit: int | None,
    runtime_mode: RuntimeMode,
    answer_composer_backend: str | None,
    answer_seed: int | None,
) -> dict[str, Any]:
    return {
        "questions_file": _repo_relative(questions_file),
        "material_text_file": (
            _repo_relative(material_text_file) if material_text_file else None
        ),
        "material_pdf_file": (
            _repo_relative(material_pdf_file) if material_pdf_file else None
        ),
        "question_limit": question_limit,
        "runtime_mode": runtime_mode,
        "answer_composer_backend_override": answer_composer_backend,
        "answer_seed": answer_seed,
        "answer_seed_specified": answer_seed is not None,
    }


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [item for item in _list(value) if isinstance(item, str)]


def _text(value: object, *, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a TripProof question dataset through product APIs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where a timestamped run folder will be written.",
    )
    parser.add_argument(
        "--questions-file",
        type=Path,
        default=DEFAULT_QUESTIONS_FILE,
        help="Question dataset JSON file.",
    )
    parser.add_argument(
        "--material-text-file",
        type=Path,
        default=None,
        help="Text fixture that will be rendered into a temporary PDF upload.",
    )
    parser.add_argument(
        "--material-pdf-file",
        type=Path,
        default=None,
        help="Original PDF file that will be uploaded as-is for a baseline run.",
    )
    parser.add_argument("--run-id", help="Optional slug for the run folder.")
    parser.add_argument(
        "--correlation-prefix",
        help="Optional prefix for generated per-question correlation ids.",
    )
    parser.add_argument(
        "--question-limit",
        type=int,
        help="Limit the number of questions for a quick local run.",
    )
    parser.add_argument(
        "--runtime-mode",
        default=RUNTIME_MODE_PRODUCTION,
        choices=(RUNTIME_MODE_PRODUCTION, RUNTIME_MODE_DETERMINISTIC),
        help=(
            "Runtime mode. production uses the app's configured product runtime; "
            "deterministic uses fake embeddings, memory retrieval, and a missing "
            "composer unless explicitly overridden."
        ),
    )
    parser.add_argument(
        "--answer-composer-backend",
        default=None,
        choices=("missing", "disabled", "ollama"),
        help=("Optional answer composer backend override. Omit for production config."),
    )
    parser.add_argument(
        "--answer-seed",
        type=int,
        default=None,
        help=(
            "Optional Ollama answer seed for runs that use the Ollama answer "
            "composer. Recorded in run artifacts."
        ),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run the same dataset N times and write a repeat bundle artifact.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the artifact JSON with artifact_path.",
    )
    return parser.parse_args()


class DatasetEmbeddingProvider:
    def __init__(self) -> None:
        self.profile = EmbeddingProfile(
            provider="eval_fake_vector",
            model="unit-vector",
            dimensions=3,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


if __name__ == "__main__":
    raise SystemExit(main())
