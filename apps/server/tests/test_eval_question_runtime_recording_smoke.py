from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_question_runtime_recording_smoke_writes_correlation_artifacts(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "question_runtime_recording_smoke.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "smoke-test",
            "--correlation-id",
            "flow_eval_test",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = json.loads(result.stdout)
    artifact_path = Path(output["artifact_path"])
    assert artifact_path == tmp_path / "smoke-test" / "run.json"
    assert artifact_path.exists()

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert (
        artifact["schema_version"] == "tripproof.eval_run.question_runtime_recording.v1"
    )
    assert artifact["correlation_id"] == "flow_eval_test"
    assert artifact["requests"]["material_upload"]["request_id"].startswith("req_")
    assert (
        artifact["requests"]["material_upload"]["correlation_id"]
        == artifact["requests"]["material_upload"]["request_id"]
    )
    assert artifact["requests"]["question_answer"]["request_id"].startswith("req_")
    assert artifact["requests"]["question_answer"]["correlation_id"] == "flow_eval_test"
    assert artifact["observed_answer"]["status"] == "accepted"
    assert artifact["observed_answer"]["evidence_state_counts"] == {"supported": 1}
    assert artifact["question_results"][0]["id"] == "SMOKE-QUESTION"
    assert artifact["question_results"][0]["status_code"] == 200
    assert artifact["question_results"][0]["expected"]["evidence_state"] == "supported"
    assert artifact["question_results"][0]["observed"]["answer_items"][0]["body"] == (
        "Check-in starts at 15:00."
    )
    assert artifact["question_results"][0]["rule_check"] == {
        "missing_cues": [],
        "must_not_hits": [],
        "passed": True,
        "state_matched": True,
    }
    assert all(artifact["checks"].values())

    observation_export_path = (
        artifact_path.parent / artifact["observation_export"]["path"]
    )
    rows = [
        json.loads(line)
        for line in observation_export_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["operation"] for row in rows] == ["material_upload", "question_answer"]
    assert rows[1]["correlation_id"] == "flow_eval_test"
    observation_json = json.dumps(rows, ensure_ascii=False)
    assert "required_evidence_cues" not in observation_json
    assert "must_not_claim" not in observation_json
    assert "rule_check" not in observation_json
    assert "expected" not in observation_json

    report_path = artifact_path.parent / artifact["html_report"]["path"]
    assert report_path == tmp_path / "smoke-test" / "report.html"
    report_html = report_path.read_text(encoding="utf-8")
    assert "TripProof eval" in report_html
    assert "SMOKE-QUESTION" in report_html
    assert "flow_eval_test" in report_html
    assert "observations/observation-export.jsonl:2" in report_html
    assert "Hotel address is Hakata. Check-in starts at 15:00." in report_html
    assert "Check-in starts at 15:00." in report_html
    assert "Composer context" in report_html
    assert "LangSmith hint" in report_html
