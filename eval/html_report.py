from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
from typing import Any

DEFAULT_REPORT_FILE_NAME = "report.html"


def main() -> int:
    args = _parse_args()
    report_path = write_html_report(
        run_json_path=args.run_json,
        output_path=args.output,
    )
    if args.json:
        print(
            json.dumps(
                {"run_json_path": str(args.run_json), "report_path": str(report_path)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"wrote {report_path}")
    return 0


def write_html_report(
    *,
    run_json_path: Path,
    output_path: Path | None = None,
) -> Path:
    run_json_path = run_json_path.resolve()
    report_path = output_path or run_json_path.parent / DEFAULT_REPORT_FILE_NAME
    report_path.write_text(
        render_html_report(run_json_path=run_json_path),
        encoding="utf-8",
    )
    return report_path


def render_html_report(*, run_json_path: Path) -> str:
    run = _read_json(run_json_path)
    run_dir = run_json_path.parent
    observations = _load_observations(run=run, run_dir=run_dir)
    questions = _question_reports(run=run, observations=observations, run_dir=run_dir)
    summary = _run_summary(run=run, questions=questions, observations=observations)

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="ko">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_h(summary.title)}</title>",
            "<style>",
            _style(),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            _render_header(run=run, summary=summary),
            _render_summary(summary),
            _render_question_table(questions),
            *[_render_question_detail(question) for question in questions],
            "</main>",
            "</body>",
            "</html>",
        ]
    )


@dataclass(frozen=True)
class ObservationRecord:
    row: dict[str, Any]
    source_path: Path
    line_number: int

    @property
    def payload(self) -> dict[str, Any]:
        return _dict(self.row.get("payload"))

    @property
    def correlation_id(self) -> str:
        return _text(self.row.get("correlation_id"))

    @property
    def operation(self) -> str:
        return _text(self.row.get("operation"), fallback="unknown_operation")

    @property
    def record_id(self) -> str:
        return _text(self.row.get("record_id"), fallback="unknown_record")

    @property
    def request_id(self) -> str:
        return _text(self.row.get("request_id"), fallback="unknown_request")

    @property
    def final_status(self) -> str:
        return _text(self.payload.get("final_status"), fallback="unknown_status")

    @property
    def failure_kind(self) -> str:
        return _text(self.payload.get("failure_kind"), fallback="none")

    def relative_source(self, run_dir: Path) -> str:
        try:
            source = self.source_path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            source = self.source_path
        return f"{source}:{self.line_number}"


@dataclass(frozen=True)
class QuestionReport:
    id: str
    priority: str
    question_text: str
    correlation_id: str
    request_id: str
    expected_state: str
    observed_states: dict[str, int]
    product_status: str
    rule_passed: bool | None
    missing_cues: list[str]
    must_not_hits: list[str]
    answer_summary: str
    answer_items: list[dict[str, Any]]
    retrieval_candidates: list[dict[str, Any]]
    context_blocks: list[dict[str, Any]]
    answer_projection: dict[str, Any]
    observation: ObservationRecord | None
    observation_source: str


@dataclass(frozen=True)
class RunSummary:
    title: str
    question_count: int
    passed_rule_checks: int
    failed_rule_checks: int
    request_failures: int
    expected_state_counts: dict[str, int]
    observed_state_counts: dict[str, int]
    observation_count: int


def _run_summary(
    *,
    run: dict[str, Any],
    questions: list[QuestionReport],
    observations: list[ObservationRecord],
) -> RunSummary:
    expected_state_counts = Counter(
        question.expected_state
        for question in questions
        if question.expected_state != "not_recorded"
    )
    observed_state_counts: Counter[str] = Counter()
    for question in questions:
        observed_state_counts.update(question.observed_states)

    return RunSummary(
        title=f"TripProof eval report · {_text(run.get('run_id'), fallback='run')}",
        question_count=len(questions),
        passed_rule_checks=sum(
            1 for question in questions if question.rule_passed is True
        ),
        failed_rule_checks=sum(
            1 for question in questions if question.rule_passed is False
        ),
        request_failures=sum(
            1
            for request in _dict(run.get("requests")).values()
            if isinstance(request, dict) and request.get("status_code") != 200
        )
        + sum(
            1
            for question in _list(run.get("question_results"))
            if isinstance(question, dict)
            and isinstance(question.get("status_code"), int)
            and question.get("status_code") != 200
        ),
        expected_state_counts=dict(expected_state_counts),
        observed_state_counts=dict(observed_state_counts),
        observation_count=len(observations),
    )


def _question_reports(
    *,
    run: dict[str, Any],
    observations: list[ObservationRecord],
    run_dir: Path,
) -> list[QuestionReport]:
    by_correlation_id: dict[str, ObservationRecord] = {}
    for observation in observations:
        if observation.operation != "question_answer":
            continue
        by_correlation_id.setdefault(observation.correlation_id, observation)

    question_results = _list(run.get("question_results"))
    if not question_results:
        question_results = [_legacy_smoke_question_result(run)]

    reports = []
    for index, question in enumerate(question_results, start=1):
        if not isinstance(question, dict):
            continue
        correlation_id = _text(
            question.get("correlation_id"),
            fallback=_text(run.get("correlation_id")),
        )
        observation = by_correlation_id.get(correlation_id)
        expected = _dict(question.get("expected"))
        observed = _dict(question.get("observed"))
        rule_check = _dict(question.get("rule_check"))
        answer_projection = _step_facts(observation, "answer_projection")
        product_answer_items = _list(observed.get("answer_items")) or _list(
            answer_projection.get("items")
        )

        reports.append(
            QuestionReport(
                id=_text(question.get("id"), fallback=f"question-{index}"),
                priority=_text(question.get("priority"), fallback="not_recorded"),
                question_text=_text(question.get("question")),
                correlation_id=correlation_id,
                request_id=_text(question.get("request_id"), fallback="not_recorded"),
                expected_state=_text(
                    expected.get("evidence_state"), fallback="not_recorded"
                ),
                observed_states=_observed_states(observed=observed, question=question),
                product_status=_text(
                    observed.get("status"),
                    fallback=_text(question.get("product_status"), fallback="unknown"),
                ),
                rule_passed=_bool_or_none(rule_check.get("passed")),
                missing_cues=_string_list(rule_check.get("missing_cues")),
                must_not_hits=_string_list(rule_check.get("must_not_hits")),
                answer_summary=_text(observed.get("answer_summary")),
                answer_items=[
                    item for item in product_answer_items if isinstance(item, dict)
                ],
                retrieval_candidates=[
                    item
                    for item in _list(
                        _step_facts(observation, "candidate_summary").get("candidates")
                    )
                    if isinstance(item, dict)
                ],
                context_blocks=[
                    item
                    for item in _list(
                        _step_facts(observation, "context_assembly").get(
                            "context_blocks"
                        )
                    )
                    if isinstance(item, dict)
                ],
                answer_projection=answer_projection,
                observation=observation,
                observation_source=(
                    observation.relative_source(run_dir=run_dir)
                    if observation is not None
                    else "not_found"
                ),
            )
        )
    return reports


def _legacy_smoke_question_result(run: dict[str, Any]) -> dict[str, Any]:
    request = _dict(_dict(run.get("requests")).get("question_answer"))
    observed_answer = _dict(run.get("observed_answer"))
    checks = _dict(run.get("checks"))
    return {
        "id": "question_answer",
        "priority": "smoke",
        "question": _text(run.get("question")),
        "correlation_id": _text(run.get("correlation_id")),
        "request_id": _text(request.get("request_id")),
        "expected": {},
        "observed": {
            "status": observed_answer.get("status"),
            "answer_summary": observed_answer.get("summary"),
            "evidence_state_counts": observed_answer.get("evidence_state_counts"),
        },
        "rule_check": {
            "passed": all(value is True for value in checks.values()),
            "missing_cues": [],
            "must_not_hits": [],
        },
    }


def _observed_states(
    *,
    observed: dict[str, Any],
    question: dict[str, Any],
) -> dict[str, int]:
    evidence_counts = observed.get("evidence_state_counts")
    if isinstance(evidence_counts, dict):
        return {
            str(key): value
            for key, value in evidence_counts.items()
            if isinstance(value, int)
        }
    fallback = question.get("observed_states")
    if isinstance(fallback, dict):
        return {
            str(key): value for key, value in fallback.items() if isinstance(value, int)
        }
    return {}


def _load_observations(
    *,
    run: dict[str, Any],
    run_dir: Path,
) -> list[ObservationRecord]:
    export = _dict(run.get("observation_export"))
    export_path = _text(export.get("path"))
    if export_path == "":
        return []
    source_path = run_dir / export_path
    if not source_path.exists():
        return []
    records = []
    for line_number, line in enumerate(
        source_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            records.append(
                ObservationRecord(
                    row=row,
                    source_path=source_path,
                    line_number=line_number,
                )
            )
    return records


def _step_facts(
    observation: ObservationRecord | None,
    step_name: str,
) -> dict[str, Any]:
    if observation is None:
        return {}
    step = _find_step(_list(observation.payload.get("steps")), step_name)
    if step is None:
        return {}
    return _dict(step.get("facts"))


def _find_step(steps: list[Any], step_name: str) -> dict[str, Any] | None:
    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("name") == step_name:
            return step
        child = _find_step(_list(step.get("children")), step_name)
        if child is not None:
            return child
    return None


def _render_header(*, run: dict[str, Any], summary: RunSummary) -> str:
    return "".join(
        [
            '<section class="hero">',
            "<div>",
            '<p class="eyebrow">TripProof eval</p>',
            f"<h1>{_h(_text(run.get('run_id'), fallback='run'))}</h1>",
            f"<p>{_h(_text(run.get('kind'), fallback='eval run'))}</p>",
            "</div>",
            "<dl>",
            _stat("created", _text(run.get("created_at"), fallback="not recorded")),
            _stat("questions", str(summary.question_count)),
            _stat("observations", str(summary.observation_count)),
            "</dl>",
            "</section>",
        ]
    )


def _render_summary(summary: RunSummary) -> str:
    return "".join(
        [
            "<section>",
            "<h2>Run summary</h2>",
            '<div class="summary-grid">',
            _metric("Question count", summary.question_count),
            _metric("Passed rule checks", summary.passed_rule_checks),
            _metric("Failed rule checks", summary.failed_rule_checks),
            _metric("Request failures", summary.request_failures),
            _metric("Expected states", _compact_counts(summary.expected_state_counts)),
            _metric("Observed states", _compact_counts(summary.observed_state_counts)),
            "</div>",
            "</section>",
        ]
    )


def _render_question_table(questions: list[QuestionReport]) -> str:
    rows = "".join(
        "<tr>"
        f'<td><a href="#{_anchor(question.id)}">{_h(question.id)}</a></td>'
        f"<td>{_h(question.priority)}</td>"
        f"<td>{_h(question.expected_state)}</td>"
        f"<td>{_h(_compact_counts(question.observed_states))}</td>"
        f"<td>{_h(_rule_label(question.rule_passed))}</td>"
        f"<td>{_h(_list_label(question.missing_cues))}</td>"
        f"<td>{_h(_list_label(question.must_not_hits))}</td>"
        "</tr>"
        for question in questions
    )
    return "".join(
        [
            "<section>",
            "<h2>Questions</h2>",
            '<div class="table-wrap">',
            "<table>",
            "<thead><tr>",
            "<th>ID</th><th>Priority</th><th>Expected</th><th>Observed</th>",
            "<th>Rule</th><th>Missing cues</th><th>Must-not hits</th>",
            "</tr></thead>",
            f"<tbody>{rows}</tbody>",
            "</table>",
            "</div>",
            "</section>",
        ]
    )


def _render_question_detail(question: QuestionReport) -> str:
    return "".join(
        [
            f'<section id="{_anchor(question.id)}" class="question-detail">',
            f"<h2>{_h(question.id)}</h2>",
            '<dl class="meta-grid">',
            _stat("correlation_id", question.correlation_id),
            _stat("request_id", question.request_id),
            _stat("product_status", question.product_status),
            _stat("observation", question.observation_source),
            _stat("LangSmith hint", f"search correlation_id:{question.correlation_id}"),
            "</dl>",
            "<h3>Question</h3>",
            f"<p>{_h(question.question_text or 'question text not recorded')}</p>",
            "<h3>Product answer</h3>",
            f"<p>{_h(question.answer_summary or 'summary not recorded')}</p>",
            _render_answer_items(question.answer_items),
            "<h3>Retrieval candidates</h3>",
            _render_text_blocks(question.retrieval_candidates, kind="candidate"),
            "<h3>Composer context</h3>",
            _render_text_blocks(question.context_blocks, kind="context"),
            "<h3>Answer projection facts</h3>",
            _render_json(question.answer_projection),
            "</section>",
        ]
    )


def _render_answer_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">No answer items recorded in observation.</p>'
    rendered = []
    for item in items:
        evidence = _list(item.get("evidence"))
        rendered_evidence = "".join(
            "<li>"
            f"<span>{_h(_text(ref.get('source_unit_id') if isinstance(ref, dict) else ''))}</span>"
            f"<code>{_h(_text(ref.get('locator') if isinstance(ref, dict) else ''))}</code>"
            f"<blockquote>{_h(_text(ref.get('snippet') if isinstance(ref, dict) else ''))}</blockquote>"
            "</li>"
            for ref in evidence
            if isinstance(ref, dict)
        )
        rendered.append(
            '<article class="answer-item">'
            f"<h4>{_h(_text(item.get('label'), fallback='item'))}</h4>"
            f"<p>{_h(_text(item.get('body'), fallback=''))}</p>"
            f"<p class=\"pill\">{_h(_text(item.get('evidence_state'), fallback='unknown'))}</p>"
            f'<ul class="evidence-list">{rendered_evidence}</ul>'
            "</article>"
        )
    return "".join(rendered)


def _render_text_blocks(blocks: list[dict[str, Any]], *, kind: str) -> str:
    if not blocks:
        return f'<p class="empty">No {kind} text recorded in observation.</p>'
    rendered = []
    for block in blocks:
        score = block.get("score")
        score_text = f" · score {score}" if isinstance(score, int | float) else ""
        rendered.append(
            '<article class="text-block">'
            "<header>"
            f"<span>{_h(_text(block.get('source_unit_id'), fallback='source_unit'))}</span>"
            f"<code>{_h(_text(block.get('locator'), fallback='locator'))}</code>"
            f"<small>{_h(str(_int_or_text(block.get('char_length'))))} chars{_h(score_text)}</small>"
            "</header>"
            f"<pre>{_h(_text(block.get('text'), fallback=''))}</pre>"
            "</article>"
        )
    return "".join(rendered)


def _render_json(value: object) -> str:
    return (
        '<pre class="json">'
        + _h(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
        + "</pre>"
    )


def _metric(label: str, value: object) -> str:
    return (
        '<div class="metric">'
        f"<span>{_h(label)}</span>"
        f"<strong>{_h(str(value))}</strong>"
        "</div>"
    )


def _stat(label: str, value: object) -> str:
    return f"<dt>{_h(label)}</dt><dd>{_h(str(value))}</dd>"


def _style() -> str:
    return """
:root {
  color-scheme: light;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #1f2933;
  background: #f6f8fa;
}
body {
  margin: 0;
}
main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 20px 64px;
}
section {
  margin-top: 24px;
}
.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  padding-bottom: 20px;
  border-bottom: 1px solid #d8dee4;
}
.hero h1 {
  margin: 0;
  font-size: 32px;
}
.hero p {
  margin: 8px 0 0;
  color: #5b6472;
}
.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: .08em;
  color: #52616f;
}
h2 {
  margin: 0 0 12px;
  font-size: 20px;
}
h3 {
  margin: 24px 0 10px;
  font-size: 16px;
}
h4 {
  margin: 0 0 8px;
  font-size: 15px;
}
dl {
  margin: 0;
}
dt {
  font-size: 12px;
  color: #667085;
}
dd {
  margin: 2px 0 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  overflow-wrap: anywhere;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
}
.metric,
.answer-item,
.text-block {
  border: 1px solid #d8dee4;
  border-radius: 8px;
  background: #fff;
  padding: 14px;
}
.metric span {
  display: block;
  color: #667085;
  font-size: 12px;
}
.metric strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid #d8dee4;
  border-radius: 8px;
  background: #fff;
}
table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}
th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}
th {
  font-size: 12px;
  color: #52616f;
  background: #eef2f6;
}
.question-detail {
  padding-top: 8px;
  border-top: 1px solid #d8dee4;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 16px;
}
.answer-item,
.text-block {
  margin-top: 10px;
}
.pill {
  display: inline-block;
  margin: 2px 0 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef6ff;
  color: #1d4f7a;
  font-size: 12px;
}
.evidence-list {
  margin: 10px 0 0;
  padding-left: 20px;
}
.evidence-list blockquote {
  margin: 6px 0 0;
  color: #334155;
}
.text-block header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: #52616f;
  font-size: 12px;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #eef2f6;
  border-radius: 4px;
  padding: 2px 5px;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 10px 0 0;
  padding: 12px;
  border-radius: 6px;
  background: #f8fafc;
}
.json {
  border: 1px solid #d8dee4;
}
.empty {
  color: #667085;
}
""".strip()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: object) -> list[str]:
    return [item for item in _list(value) if isinstance(item, str)]


def _text(value: object, *, fallback: str = "") -> str:
    return value if isinstance(value, str) else fallback


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _compact_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "not recorded"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def _list_label(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _rule_label(value: bool | None) -> str:
    if value is True:
        return "passed"
    if value is False:
        return "failed"
    return "not recorded"


def _anchor(value: str) -> str:
    return (
        "".join(
            character.lower() if character.isalnum() else "-"
            for character in value.strip()
        ).strip("-")
        or "question"
    )


def _int_or_text(value: object) -> object:
    return value if isinstance(value, int) else "unknown"


def _h(value: object) -> str:
    return escape(str(value), quote=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a TripProof eval run HTML report.",
    )
    parser.add_argument("run_json", type=Path, help="Path to eval run.json.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write report HTML. Defaults to report.html next to run.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable output paths.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
