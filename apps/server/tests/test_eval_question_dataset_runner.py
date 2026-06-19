from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def test_question_dataset_runner_writes_joined_html_report(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "run_question_dataset.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "dataset-test",
            "--correlation-prefix",
            "dataset_eval_test",
            "--question-limit",
            "2",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = json.loads(result.stdout)
    artifact_path = Path(output["artifact_path"])
    assert artifact_path == tmp_path / "dataset-test" / "run.json"
    assert artifact_path.exists()

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == "tripproof.eval_run.question_dataset.v1"
    assert artifact["run_purpose"]["id"] == "sample_fixture_smoke"
    assert artifact["run_purpose"]["agoda_original_pdf_baseline"] is False
    assert artifact["run_purpose"]["sample_fixture_smoke"] is True
    assert artifact["dataset"]["question_count"] == 2
    assert artifact["dataset"]["material_input"] == {
        "kind": "text_fixture_rendered_pdf",
        "source_path": "fixtures/accommodation-checkin/agoda-booking-confirmation-sample.txt",
        "uploaded_file_name": "agoda-booking-confirmation-sample.pdf",
    }
    assert artifact["runtime"]["embedding_provider"] == "eval_fake_vector"
    assert artifact["question_results"][0]["id"] == "AGODA-P0-01"
    assert artifact["question_results"][0]["status_code"] == 200
    assert artifact["question_results"][0]["correlation_id"] == (
        "dataset_eval_test_AGODA-P0-01"
    )
    assert artifact["question_results"][0]["observed"]["answer_items"][0]["body"] == (
        "현재 등록된 자료에서 질문에 대한 답을 확인하지 못했습니다."
    )
    assert artifact["question_results"][0]["rule_check"]["passed"] is False
    assert all(artifact["checks"].values())

    observation_export_path = (
        artifact_path.parent / artifact["observation_export"]["path"]
    )
    rows = [
        json.loads(line)
        for line in observation_export_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["operation"] for row in rows] == [
        "material_upload",
        "question_answer",
        "question_answer",
    ]
    assert rows[1]["correlation_id"] == "dataset_eval_test_AGODA-P0-01"
    observation_json = json.dumps(rows, ensure_ascii=False)
    assert "required_evidence_cues" not in observation_json
    assert "rule_check" not in observation_json
    assert "Agoda Fukuoka sample booking confirmation" in observation_json

    report_path = artifact_path.parent / artifact["html_report"]["path"]
    report_html = report_path.read_text(encoding="utf-8")
    assert "AGODA-P0-01" in report_html
    assert "Sample fixture smoke" in report_html
    assert "Text fixture rendered as PDF" in report_html
    assert "Agoda original PDF baseline으로 해석하지 않습니다" in report_html
    assert "dataset_eval_test_AGODA-P0-01" in report_html
    assert "observations/observation-export.jsonl:2" in report_html
    assert "Agoda Fukuoka sample booking confirmation" in report_html
    assert "TripProof Hakata Sample Hotel" in report_html
    assert "Source" in report_html
    assert (
        "fixtures/accommodation-checkin/agoda-booking-confirmation-sample.txt"
        in report_html
    )
    assert "source location" in report_html
    assert "Eval verdict" in report_html
    assert "Eval overlay" in report_html
    assert "Observation trace" in report_html
    assert "Product runtime" in report_html
    assert "Raw observation step JSON" in report_html
    assert "Raw observation JSON" in report_html
    assert "Evidence path" in report_html
    assert "Data lineage" in report_html
    assert "Failure classification cues" in report_html
    assert "Failure reading" in report_html
    assert "State validation" in report_html
    assert "SourceUnit" in report_html
    assert "EvidenceRef" in report_html
    assert "SourceUnit text" in report_html
    assert "sent_to_composer" in report_html
    assert "No EvidenceRef created for this run." in report_html
    assert "source_retrieval" in report_html
    assert "candidate_summary" in report_html
    assert "context_assembly" in report_html
    assert "composer_call" in report_html
    assert "answer_projection" in report_html
    assert "판정 요약" in report_html
    assert "제품이 사용자에게 돌려준 답" in report_html
    assert "검색된 근거 후보" in report_html
    assert "Retrieval candidates" in report_html
    assert "답변에 전달된 context" in report_html
    assert "Composer context" in report_html


def test_question_dataset_runner_accepts_original_pdf_baseline_input(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "run_question_dataset.py"
    material_pdf_file = tmp_path / "agoda-original.pdf"
    material_pdf_file.write_bytes(
        _pdf_with_text("Agoda original PDF baseline. Check-in starts at 15:00.")
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(tmp_path),
            "--material-pdf-file",
            str(material_pdf_file),
            "--run-id",
            "original-pdf-baseline-test",
            "--correlation-prefix",
            "original_pdf_eval",
            "--question-limit",
            "1",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = json.loads(result.stdout)
    artifact_path = Path(output["artifact_path"])
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["run_purpose"]["id"] == "original_pdf_baseline"
    assert artifact["run_purpose"]["agoda_original_pdf_baseline"] is True
    assert artifact["run_purpose"]["sample_fixture_smoke"] is False
    assert artifact["dataset"]["material_pdf_file"] == str(material_pdf_file)
    assert artifact["dataset"]["material_input"] == {
        "kind": "pdf_file",
        "source_path": str(material_pdf_file),
        "uploaded_file_name": "agoda-original.pdf",
    }
    assert "material_text_file" not in artifact["dataset"]
    assert artifact["question_results"][0]["id"] == "AGODA-P0-01"
    assert artifact["question_results"][0]["status_code"] == 200
    assert all(artifact["checks"].values())

    report_html = (artifact_path.parent / artifact["html_report"]["path"]).read_text(
        encoding="utf-8"
    )
    assert "Original PDF baseline" in report_html
    assert "Original PDF file" in report_html
    assert str(material_pdf_file) in report_html
    assert "이 run은 원문 PDF baseline입니다" in report_html
    assert "Agoda original PDF baseline으로 해석하지 않습니다" not in report_html


def test_question_dataset_runner_makes_correlation_ids_unique_on_collisions(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "run_question_dataset.py"
    questions_file = tmp_path / "questions.json"
    material_text_file = tmp_path / "material.txt"
    questions_file.write_text(
        json.dumps(
            [
                {
                    "id": "DUP/A",
                    "priority": "p0",
                    "type": "fact",
                    "question": "check-in time?",
                    "expected_evidence_state": "supported",
                    "required_evidence_cues": [],
                    "must_not_claim": [],
                },
                {
                    "id": "DUP A",
                    "priority": "p0",
                    "type": "fact",
                    "question": "hotel address?",
                    "expected_evidence_state": "supported",
                    "required_evidence_cues": [],
                    "must_not_claim": [],
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    material_text_file.write_text(
        "Hotel address is Hakata. Check-in starts at 15:00.",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(tmp_path),
            "--questions-file",
            str(questions_file),
            "--material-text-file",
            str(material_text_file),
            "--run-id",
            "collision-test",
            "--correlation-prefix",
            "collision_eval",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = json.loads(result.stdout)
    artifact = json.loads(Path(output["artifact_path"]).read_text(encoding="utf-8"))
    correlation_ids = [
        question["correlation_id"] for question in artifact["question_results"]
    ]

    assert correlation_ids[0] == "collision_eval_DUP_A"
    assert correlation_ids[1].startswith("collision_eval_DUP_A_2_")
    assert len(correlation_ids) == len(set(correlation_ids))
    assert artifact["checks"]["generated_question_correlation_ids_unique"] is True
    assert artifact["checks"]["all_question_exports_correlation_matched_inputs"] is True


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


def test_html_report_keeps_product_answer_and_observation_projection_separate(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "html_report.py"
    run_path = tmp_path / "run.json"
    observation_path = tmp_path / "observations" / "observation-export.jsonl"
    observation_path.parent.mkdir()
    observation_path.write_text(
        json.dumps(
            {
                "schema_version": "tripproof.observation_export.v1",
                "operation": "question_answer",
                "record_id": "obs_question_1",
                "request_id": "req_question",
                "correlation_id": "flow_eval_test",
                "payload": {
                    "subject": {},
                    "final_status": "accepted",
                    "failure_kind": None,
                    "steps": [
                        {
                            "name": "answer_projection",
                            "status": "succeeded",
                            "failure_kind": None,
                            "facts": {
                                "item_count": 1,
                                "evidence_state_counts": {"supported": 1},
                                "items": [
                                    {
                                        "id": "answer",
                                        "label": "Observation item",
                                        "body": "Observation projection body",
                                        "value": None,
                                        "evidence_state": "supported",
                                        "evidence": [],
                                    }
                                ],
                            },
                            "children": [],
                        }
                    ],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    run_path.write_text(
        json.dumps(
            {
                "schema_version": "tripproof.eval_run.question_dataset.v1",
                "run_id": "report-source-test",
                "kind": "question_dataset",
                "created_at": "2026-06-19T00:00:00Z",
                "requests": {},
                "question_results": [
                    {
                        "id": "QUESTION-1",
                        "priority": "p0",
                        "question": "What is the answer?",
                        "correlation_id": "flow_eval_test",
                        "request_id": "req_question",
                        "status_code": 200,
                        "expected": {"evidence_state": "supported"},
                        "observed": {
                            "status": "accepted",
                            "answer_summary": "Product summary",
                            "answer_items": [
                                {
                                    "id": "answer",
                                    "label": "Product item",
                                    "body": "Product response body",
                                    "value": None,
                                    "evidence_state": "supported",
                                    "evidence": [],
                                }
                            ],
                            "evidence_state_counts": {"supported": 1},
                        },
                        "rule_check": {
                            "passed": True,
                            "missing_cues": [],
                            "must_not_hits": [],
                        },
                    }
                ],
                "observation_export": {
                    "path": "observations/observation-export.jsonl",
                    "record_count": 1,
                    "records": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(script), str(run_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    report_html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Product response body" in report_html
    assert "Observation projection body" in report_html
    assert report_html.index("Product response body") < report_html.index(
        "Answer projection facts"
    )
    assert "제품이 사용자에게 돌려준 답" in report_html
    assert "Raw details" in report_html


def test_html_report_uses_request_id_when_correlation_id_is_duplicated(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "html_report.py"
    run_path = tmp_path / "run.json"
    observation_path = tmp_path / "observations" / "observation-export.jsonl"
    observation_path.parent.mkdir()
    observation_rows = [
        {
            "schema_version": "tripproof.observation_export.v1",
            "operation": "question_answer",
            "record_id": "obs_question_1",
            "request_id": "req_first",
            "correlation_id": "duplicated_correlation",
            "payload": {
                "subject": {},
                "final_status": "accepted",
                "failure_kind": None,
                "steps": [
                    {
                        "name": "answer_projection",
                        "status": "succeeded",
                        "failure_kind": None,
                        "facts": {
                            "item_count": 1,
                            "evidence_state_counts": {"supported": 1},
                            "items": [
                                {
                                    "id": "answer",
                                    "label": "Observation item",
                                    "body": "First observation body",
                                    "value": None,
                                    "evidence_state": "supported",
                                    "evidence": [],
                                }
                            ],
                        },
                        "children": [],
                    }
                ],
            },
        },
        {
            "schema_version": "tripproof.observation_export.v1",
            "operation": "question_answer",
            "record_id": "obs_question_2",
            "request_id": "req_second",
            "correlation_id": "duplicated_correlation",
            "payload": {
                "subject": {},
                "final_status": "accepted",
                "failure_kind": None,
                "steps": [
                    {
                        "name": "answer_projection",
                        "status": "succeeded",
                        "failure_kind": None,
                        "facts": {
                            "item_count": 1,
                            "evidence_state_counts": {"supported": 1},
                            "items": [
                                {
                                    "id": "answer",
                                    "label": "Observation item",
                                    "body": "Second observation body",
                                    "value": None,
                                    "evidence_state": "supported",
                                    "evidence": [],
                                }
                            ],
                        },
                        "children": [],
                    }
                ],
            },
        },
    ]
    observation_path.write_text(
        "\n".join(json.dumps(row) for row in observation_rows) + "\n",
        encoding="utf-8",
    )
    run_path.write_text(
        json.dumps(
            {
                "schema_version": "tripproof.eval_run.question_dataset.v1",
                "run_id": "duplicate-correlation-report-test",
                "kind": "question_dataset",
                "created_at": "2026-06-19T00:00:00Z",
                "requests": {},
                "question_results": [
                    {
                        "id": "QUESTION-1",
                        "priority": "p0",
                        "question": "first?",
                        "correlation_id": "duplicated_correlation",
                        "request_id": "req_first",
                        "status_code": 200,
                        "expected": {"evidence_state": "supported"},
                        "observed": {
                            "status": "accepted",
                            "answer_summary": "First product summary",
                            "answer_items": [],
                            "evidence_state_counts": {"supported": 1},
                        },
                        "rule_check": {
                            "passed": True,
                            "missing_cues": [],
                            "must_not_hits": [],
                        },
                    },
                    {
                        "id": "QUESTION-2",
                        "priority": "p0",
                        "question": "second?",
                        "correlation_id": "duplicated_correlation",
                        "request_id": "req_second",
                        "status_code": 200,
                        "expected": {"evidence_state": "supported"},
                        "observed": {
                            "status": "accepted",
                            "answer_summary": "Second product summary",
                            "answer_items": [],
                            "evidence_state_counts": {"supported": 1},
                        },
                        "rule_check": {
                            "passed": True,
                            "missing_cues": [],
                            "must_not_hits": [],
                        },
                    },
                ],
                "observation_export": {
                    "path": "observations/observation-export.jsonl",
                    "record_count": 2,
                    "records": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(script), str(run_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    report_html = (tmp_path / "report.html").read_text(encoding="utf-8")
    first_section = report_html.split('id="question-1"', maxsplit=1)[1].split(
        'id="question-2"', maxsplit=1
    )[0]
    second_section = report_html.split('id="question-2"', maxsplit=1)[1]

    assert "observations/observation-export.jsonl:1" in first_section
    assert "First observation body" in first_section
    assert "Second observation body" not in first_section
    assert "observations/observation-export.jsonl:2" in second_section
    assert "Second observation body" in second_section
