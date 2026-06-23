from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

os.environ.setdefault("TRIPPROOF_EMBEDDING_AUTO_GENERATE", "0")
os.environ.setdefault("TRIPPROOF_SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("TRIPPROOF_SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_PATH = REPO_ROOT / "apps"
if str(APPS_PATH) not in sys.path:
    sys.path.insert(0, str(APPS_PATH))

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfWriter  # noqa: E402
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)  # noqa: E402

from server.app import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    create_app,
)  # noqa: E402
from server.extraction.models import EvidenceRef, EvidenceState  # noqa: E402
from server.observations.export import LocalArtifactObservationExporter  # noqa: E402
from server.testing import InMemoryRetrievalRepository  # noqa: E402
from server.schemas.answers import (
    ChatAnswerItemResponse,
    ChatAnswerResponse,
)  # noqa: E402
from server.schemas.evidence import EvidenceRefResponse  # noqa: E402
from html_report import DEFAULT_REPORT_FILE_NAME, write_html_report  # noqa: E402

DEFAULT_MATERIAL_TEXT = "Hotel address is Hakata. Check-in starts at 15:00."
DEFAULT_QUESTION = "check-in time?"
DEFAULT_QUESTION_ID = "SMOKE-QUESTION"
DEFAULT_QUESTION_PRIORITY = "smoke"
DEFAULT_EXPECTED_EVIDENCE_STATE = "supported"
DEFAULT_ANSWER_BODY = "Check-in starts at 15:00."
DEFAULT_EVIDENCE_SNIPPET = "Check-in starts at 15:00."
DEFAULT_REQUIRED_EVIDENCE_CUES = ("Check-in starts at 15:00",)
DEFAULT_MUST_NOT_CLAIM = ("18:00",)
RUN_SCHEMA_VERSION = "tripproof.eval_run.question_runtime_recording.v1"


def main() -> int:
    args = _parse_args()
    artifact, artifact_path = run_smoke_eval(
        output_dir=args.output_dir,
        run_id=args.run_id,
        correlation_id=args.correlation_id,
        question=args.question,
        material_text=args.material_text,
    )
    if args.json:
        printed = {**artifact, "artifact_path": str(artifact_path)}
        print(json.dumps(printed, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"wrote {artifact_path}")
    return 0


def run_smoke_eval(
    *,
    output_dir: Path,
    run_id: str | None = None,
    correlation_id: str | None = None,
    question: str = DEFAULT_QUESTION,
    material_text: str = DEFAULT_MATERIAL_TEXT,
) -> tuple[dict[str, object], Path]:
    active_run_id = _run_id(run_id)
    active_correlation_id = correlation_id or f"eval_{uuid4()}"
    run_dir = output_dir / active_run_id
    observation_dir = run_dir / "observations"
    observation_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / "run.json"

    exporter = LocalArtifactObservationExporter(observation_dir)
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_repository=InMemoryRetrievalRepository(),
            library_chat_answer_composer=StaticEvidenceAnswerComposer(),
            observation_exporter=exporter,
        )
    )

    upload = client.post(
        "/api/materials",
        data={"displayName": "Eval smoke material"},
        files={
            "file": ("booking.pdf", _pdf_with_text(material_text), "application/pdf")
        },
    )
    if upload.status_code != 200:
        raise RuntimeError(
            f"material upload failed: {upload.status_code} {upload.text}"
        )
    material = upload.json()
    material_id = material["id"]

    question_response = client.post(
        "/api/questions",
        headers={CORRELATION_ID_HEADER: active_correlation_id},
        json={"question": question, "materialIds": [material_id]},
    )
    if question_response.status_code != 200:
        raise RuntimeError(
            f"question request failed: {question_response.status_code} {question_response.text}"
        )
    question_body = question_response.json()

    observation_rows = _read_jsonl(exporter.path)
    artifact = _artifact(
        run_id=active_run_id,
        correlation_id=active_correlation_id,
        upload_response=upload,
        question_response=question_response,
        material=material,
        question_body=question_body,
        observation_export_path=Path("observations") / exporter.path.name,
        observation_rows=observation_rows,
    )
    failed_checks = [name for name, passed in artifact["checks"].items() if not passed]
    if failed_checks:
        raise RuntimeError(f"eval smoke checks failed: {', '.join(failed_checks)}")

    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_html_report(run_json_path=artifact_path)
    return artifact, artifact_path


def _artifact(
    *,
    run_id: str,
    correlation_id: str,
    upload_response,
    question_response,
    material: dict[str, object],
    question_body: dict[str, object],
    observation_export_path: Path,
    observation_rows: list[dict[str, object]],
) -> dict[str, object]:
    upload_request_id = upload_response.headers.get(REQUEST_ID_HEADER, "")
    upload_correlation_id = upload_response.headers.get(CORRELATION_ID_HEADER, "")
    question_request_id = question_response.headers.get(REQUEST_ID_HEADER, "")
    question_correlation_id = question_response.headers.get(CORRELATION_ID_HEADER, "")
    answer = (
        question_body.get("answer")
        if isinstance(question_body.get("answer"), dict)
        else {}
    )
    answer_items = (
        answer.get("items")
        if isinstance(answer, dict) and isinstance(answer.get("items"), list)
        else []
    )
    evidence_state_counts = Counter(
        item.get("evidenceState")
        for item in answer_items
        if isinstance(item, dict) and isinstance(item.get("evidenceState"), str)
    )
    observation_summaries = [
        {
            "operation": row.get("operation"),
            "request_id": row.get("request_id"),
            "correlation_id": row.get("correlation_id"),
            "final_status": _payload_value(row, "final_status"),
            "failure_kind": _payload_value(row, "failure_kind"),
        }
        for row in observation_rows
    ]

    checks = {
        "upload_response_had_request_id": upload_request_id.startswith("req_"),
        "question_response_had_request_id": question_request_id.startswith("req_"),
        "upload_request_fell_back_to_own_correlation_id": upload_correlation_id
        == upload_request_id,
        "question_response_correlation_matched_input": question_correlation_id
        == correlation_id,
        "export_contains_material_and_question": [
            row.get("operation") for row in observation_rows
        ]
        == ["material_upload", "question_answer"],
        "question_export_correlation_matched_input": any(
            row.get("operation") == "question_answer"
            and row.get("correlation_id") == correlation_id
            for row in observation_rows
        ),
        "product_json_has_no_request_or_correlation_id": _has_no_product_trace_ids(
            material
        )
        and _has_no_product_trace_ids(question_body),
    }

    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "kind": "question_runtime_recording_smoke",
        "question": DEFAULT_QUESTION,
        "correlation_id": correlation_id,
        "product_entry_point": {
            "type": "fastapi_test_client",
            "endpoints": ["POST /api/materials", "POST /api/questions"],
        },
        "runtime": {
            "retrieval_backend": "memory",
            "embedding_auto_generate": False,
            "answer_composer": "eval_static_evidence",
        },
        "requests": {
            "material_upload": {
                "status_code": upload_response.status_code,
                "request_id": upload_request_id,
                "correlation_id": upload_correlation_id,
                "material_id": material.get("id"),
                "material_status": material.get("status"),
            },
            "question_answer": {
                "status_code": question_response.status_code,
                "request_id": question_request_id,
                "correlation_id": question_correlation_id,
                "question_status": question_body.get("status"),
            },
        },
        "observed_answer": {
            "status": question_body.get("status"),
            "summary": answer.get("summary") if isinstance(answer, dict) else None,
            "item_count": len(answer_items),
            "evidence_state_counts": dict(evidence_state_counts),
            "material_count": question_body.get("materialCount"),
            "page_count": question_body.get("pageCount"),
            "char_count": question_body.get("charCount"),
        },
        "question_results": [
            _question_result(
                correlation_id=correlation_id,
                request_id=question_request_id,
                question_body=question_body,
                evidence_state_counts=dict(evidence_state_counts),
            )
        ],
        "observation_export": {
            "path": str(observation_export_path),
            "record_count": len(observation_rows),
            "records": observation_summaries,
        },
        "html_report": {"path": DEFAULT_REPORT_FILE_NAME},
        "checks": checks,
        "next_verification_point": (
            "For a real material/question run, find local observation JSONL and LangSmith trace "
            "with the same correlation_id."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a thin TripProof question runtime recording smoke eval.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "eval" / "runs" / "question-runtime-recording",
        help="Directory where a timestamped run folder will be written.",
    )
    parser.add_argument("--run-id", help="Optional slug for the run folder.")
    parser.add_argument(
        "--correlation-id", help="Optional X-TripProof-Correlation-Id value."
    )
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--material-text", default=DEFAULT_MATERIAL_TEXT)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the artifact JSON with artifact_path.",
    )
    return parser.parse_args()


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


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _payload_value(row: dict[str, object], key: str) -> object:
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _question_result(
    *,
    correlation_id: str,
    request_id: str,
    question_body: dict[str, object],
    evidence_state_counts: dict[object, int],
) -> dict[str, object]:
    answer = (
        question_body.get("answer")
        if isinstance(question_body.get("answer"), dict)
        else {}
    )
    answer_summary = answer.get("summary") if isinstance(answer, dict) else None
    answer_items = (
        answer.get("items")
        if isinstance(answer, dict) and isinstance(answer.get("items"), list)
        else []
    )
    text_for_rules = _answer_text_for_rules(answer_summary, answer_items)
    missing_cues = [
        cue for cue in DEFAULT_REQUIRED_EVIDENCE_CUES if cue not in text_for_rules
    ]
    must_not_hits = [
        claim for claim in DEFAULT_MUST_NOT_CLAIM if claim in text_for_rules
    ]
    state_matched = evidence_state_counts.get(DEFAULT_EXPECTED_EVIDENCE_STATE, 0) > 0
    return {
        "id": DEFAULT_QUESTION_ID,
        "priority": DEFAULT_QUESTION_PRIORITY,
        "question": DEFAULT_QUESTION,
        "correlation_id": correlation_id,
        "request_id": request_id,
        "status_code": 200,
        "expected": {
            "evidence_state": DEFAULT_EXPECTED_EVIDENCE_STATE,
            "required_evidence_cues": list(DEFAULT_REQUIRED_EVIDENCE_CUES),
            "must_not_claim": list(DEFAULT_MUST_NOT_CLAIM),
        },
        "observed": {
            "status": question_body.get("status"),
            "answer_summary": answer_summary,
            "answer_items": _answer_item_summaries(answer_items),
            "evidence_state_counts": evidence_state_counts,
        },
        "rule_check": {
            "passed": state_matched and not missing_cues and not must_not_hits,
            "state_matched": state_matched,
            "missing_cues": missing_cues,
            "must_not_hits": must_not_hits,
        },
    }


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


class StaticEvidenceAnswerComposer:
    def compose(self, *, question, context):
        source_unit = context.candidates[0].source_unit
        evidence_ref = EvidenceRef(
            material_id=source_unit.material_id,
            source_unit_id=source_unit.id,
            label=source_unit.file_name,
            locator=source_unit.locator,
            snippet=DEFAULT_EVIDENCE_SNIPPET,
        )
        return ChatAnswerResponse(
            summary="Grounded answer from material.",
            items=[
                ChatAnswerItemResponse(
                    id="answer",
                    label="Answer",
                    body=DEFAULT_ANSWER_BODY,
                    evidence_state=EvidenceState.SUPPORTED,
                    value=None,
                    evidence=[EvidenceRefResponse.from_domain(evidence_ref)],
                )
            ],
        )

    def runtime_answer_model_snapshot(self) -> dict[str, str | None]:
        return {
            "backend": "eval_static_evidence",
            "model": None,
        }


if __name__ == "__main__":
    raise SystemExit(main())
