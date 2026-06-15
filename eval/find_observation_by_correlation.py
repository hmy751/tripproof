from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_PATHS = (
    REPO_ROOT / ".tripproof-observations",
    REPO_ROOT / "eval" / "runs" / "question-runtime-recording",
)


def main() -> int:
    args = _parse_args()
    search_paths = tuple(args.search_path or DEFAULT_SEARCH_PATHS)
    matches = find_observations_by_correlation_id(
        correlation_id=args.correlation_id,
        search_paths=search_paths,
    )
    result = {
        "correlation_id": args.correlation_id,
        "match_count": len(matches),
        "matches": [match_to_dict(match) for match in matches],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(format_text_result(result))
    return 0 if matches else 1


def find_observations_by_correlation_id(
    *,
    correlation_id: str,
    search_paths: tuple[Path, ...],
) -> list["ObservationMatch"]:
    matches: list[ObservationMatch] = []
    for source_path in iter_jsonl_paths(search_paths):
        for line_number, row in iter_jsonl_rows(source_path):
            if row.get("correlation_id") != correlation_id:
                continue
            payload = row.get("payload")
            if not isinstance(payload, dict):
                payload = {}
            subject = payload.get("subject")
            if not isinstance(subject, dict):
                subject = {}
            matches.append(
                ObservationMatch(
                    source_path=source_path,
                    line_number=line_number,
                    schema_version=_string_or_none(row.get("schema_version")),
                    operation=_string_or_none(row.get("operation")),
                    record_id=_string_or_none(row.get("record_id")),
                    request_id=_string_or_none(row.get("request_id")),
                    correlation_id=correlation_id,
                    final_status=_string_or_none(payload.get("final_status")),
                    failure_kind=_string_or_none(payload.get("failure_kind")),
                    material_id=_string_or_none(subject.get("material_id")),
                )
            )
    return matches


def iter_jsonl_paths(search_paths: tuple[Path, ...]):
    seen: set[Path] = set()
    for search_path in search_paths:
        if not search_path.exists():
            continue
        candidates = (
            [search_path]
            if search_path.is_file()
            else sorted(search_path.rglob("*.jsonl"))
        )
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix != ".jsonl":
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


def iter_jsonl_rows(path: Path):
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield line_number, row


def match_to_dict(match: "ObservationMatch") -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_path": str(match.source_path),
        "line_number": match.line_number,
        "schema_version": match.schema_version,
        "operation": match.operation,
        "record_id": match.record_id,
        "request_id": match.request_id,
        "correlation_id": match.correlation_id,
        "final_status": match.final_status,
        "failure_kind": match.failure_kind,
    }
    if match.material_id is not None:
        result["material_id"] = match.material_id
    return result


def format_text_result(result: dict[str, Any]) -> str:
    lines = [
        f"correlation_id: {result['correlation_id']}",
        f"matches: {result['match_count']}",
    ]
    matches = result.get("matches")
    if not isinstance(matches, list) or not matches:
        lines.append("no local observation records found")
        return "\n".join(lines)

    for match in matches:
        if not isinstance(match, dict):
            continue
        operation = match.get("operation") or "unknown_operation"
        request_id = match.get("request_id") or "unknown_request"
        final_status = match.get("final_status") or "unknown_status"
        failure_kind = match.get("failure_kind") or "none"
        material_id = match.get("material_id")
        source_path = match.get("source_path")
        line_number = match.get("line_number")
        lines.append(f"- {operation} {request_id} {final_status}")
        lines.append(f"  failure_kind: {failure_kind}")
        if material_id:
            lines.append(f"  material_id: {material_id}")
        lines.append(f"  source: {source_path}:{line_number}")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find local TripProof observation export records by correlation id.",
    )
    parser.add_argument("correlation_id")
    parser.add_argument(
        "--search-path",
        type=Path,
        action="append",
        help=(
            "Directory or JSONL file to search. May be passed more than once. "
            "Defaults to .tripproof-observations/ and eval/runs/question-runtime-recording/."
        ),
    )
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON."
    )
    return parser.parse_args()


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


class ObservationMatch:
    def __init__(
        self,
        *,
        source_path: Path,
        line_number: int,
        schema_version: str | None,
        operation: str | None,
        record_id: str | None,
        request_id: str | None,
        correlation_id: str,
        final_status: str | None,
        failure_kind: str | None,
        material_id: str | None,
    ) -> None:
        self.source_path = source_path
        self.line_number = line_number
        self.schema_version = schema_version
        self.operation = operation
        self.record_id = record_id
        self.request_id = request_id
        self.correlation_id = correlation_id
        self.final_status = final_status
        self.failure_kind = failure_kind
        self.material_id = material_id


if __name__ == "__main__":
    raise SystemExit(main())
