from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_find_observation_by_correlation_returns_safe_json_summary(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "find_observation_by_correlation.py"
    export_path = tmp_path / "nested" / "observation-export.jsonl"
    export_path.parent.mkdir()
    export_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema_version": "tripproof.observation_export.v1",
                        "operation": "material_upload",
                        "record_id": "obs_material_1",
                        "request_id": "req_upload",
                        "correlation_id": "req_upload",
                        "payload": {
                            "subject": {"material_id": "mat_1"},
                            "final_status": "ready",
                            "failure_kind": None,
                        },
                    }
                ),
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
                                    "name": "query_snapshot",
                                    "facts": {"question_length": 14},
                                }
                            ],
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "flow_eval_test",
            "--search-path",
            str(tmp_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = json.loads(result.stdout)
    assert output["correlation_id"] == "flow_eval_test"
    assert output["match_count"] == 1
    assert output["matches"] == [
        {
            "source_path": str(export_path),
            "line_number": 2,
            "schema_version": "tripproof.observation_export.v1",
            "operation": "question_answer",
            "record_id": "obs_question_1",
            "request_id": "req_question",
            "correlation_id": "flow_eval_test",
            "final_status": "accepted",
            "failure_kind": None,
        }
    ]
    assert "query_snapshot" not in result.stdout
    assert "question_length" not in result.stdout


def test_find_observation_by_correlation_text_output_and_missing_exit_code(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "eval" / "find_observation_by_correlation.py"
    export_path = tmp_path / "observation-export.jsonl"
    export_path.write_text(
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
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    found = subprocess.run(
        [sys.executable, str(script), "flow_eval_test", "--search-path", str(export_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "correlation_id: flow_eval_test" in found.stdout
    assert "- question_answer req_question accepted" in found.stdout
    assert f"source: {export_path}:1" in found.stdout

    missing = subprocess.run(
        [sys.executable, str(script), "flow_missing", "--search-path", str(export_path)],
        capture_output=True,
        text=True,
    )

    assert missing.returncode == 1
    assert "matches: 0" in missing.stdout
    assert "no local observation records found" in missing.stdout
