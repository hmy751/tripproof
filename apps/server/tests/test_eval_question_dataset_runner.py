from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


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
    assert artifact["dataset"]["question_count"] == 2
    assert artifact["runtime"]["embedding_provider"] == "eval_fake_vector"
    assert artifact["question_results"][0]["id"] == "AGODA-P0-01"
    assert artifact["question_results"][0]["status_code"] == 200
    assert artifact["question_results"][0]["correlation_id"] == (
        "dataset_eval_test_AGODA-P0-01"
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
    assert "dataset_eval_test_AGODA-P0-01" in report_html
    assert "observations/observation-export.jsonl:2" in report_html
    assert "Agoda Fukuoka sample booking confirmation" in report_html
    assert "TripProof Hakata Sample Hotel" in report_html
    assert "Retrieval candidates" in report_html
    assert "Composer context" in report_html
