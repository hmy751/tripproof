from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Literal
from uuid import uuid4

os.environ.setdefault("TRIPPROOF_RETRIEVAL_BACKEND", "memory")
os.environ.setdefault("TRIPPROOF_EMBEDDING_AUTO_GENERATE", "0")
os.environ.setdefault("TRIPPROOF_FACT_PROPOSER_BACKEND", "missing")

REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_PATH = REPO_ROOT / "apps"
if str(APPS_PATH) not in sys.path:
    sys.path.insert(0, str(APPS_PATH))

from fastapi.testclient import TestClient  # noqa: E402

from html_report import DEFAULT_REPORT_FILE_NAME, write_html_report  # noqa: E402
from question_runtime_recording_smoke import (  # noqa: E402
    _answer_item_summaries,
    _answer_text_for_rules,
    _has_no_product_trace_ids,
    _pdf_with_text,
    _read_jsonl,
    _run_id,
)
from server.app import (  # noqa: E402
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    create_app,
)
from server.materials.store import MaterialStore  # noqa: E402
from server.observations.export import LocalArtifactObservationExporter  # noqa: E402
from server.retrieval.embeddings import EmbeddingProfile  # noqa: E402

RUN_SCHEMA_VERSION = "tripproof.eval_run.question_dataset.v1"
RUN_PURPOSE_ORIGINAL_PDF_BASELINE = "original_pdf_baseline"
RUN_PURPOSE_SAMPLE_FIXTURE_SMOKE = "sample_fixture_smoke"
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


def main() -> int:
    args = _parse_args()
    artifact, artifact_path = run_question_dataset(
        output_dir=args.output_dir,
        questions_file=args.questions_file,
        material_text_file=args.material_text_file,
        material_pdf_file=args.material_pdf_file,
        run_id=args.run_id,
        correlation_prefix=args.correlation_prefix,
        question_limit=args.question_limit,
        answer_composer_backend=args.answer_composer_backend,
    )
    if args.json:
        print(
            json.dumps(
                {**artifact, "artifact_path": str(artifact_path)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"wrote {artifact_path}")
    return 0


def run_question_dataset(
    *,
    output_dir: Path,
    questions_file: Path,
    material_text_file: Path | None,
    material_pdf_file: Path | None = None,
    run_id: str | None = None,
    correlation_prefix: str | None = None,
    question_limit: int | None = None,
    answer_composer_backend: str = "missing",
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
    store = MaterialStore(
        embedding_provider=DatasetEmbeddingProvider(),
        embedding_auto_generate=True,
        retrieval_backend="memory",
    )
    client = TestClient(
        create_app(
            store=store,
            fact_proposer_backend=answer_composer_backend,
            observation_exporter=exporter,
        )
    )

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
        answer_composer_backend=answer_composer_backend,
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
    answer_composer_backend: str,
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
        "runtime": {
            "retrieval_backend": "memory",
            "embedding_auto_generate": True,
            "embedding_provider": "eval_fake_vector",
            "answer_composer": answer_composer_backend,
        },
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
        "--answer-composer-backend",
        default="missing",
        choices=("missing", "disabled", "ollama"),
        help="Answer composer backend passed to the product app.",
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
