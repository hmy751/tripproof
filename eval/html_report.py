from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import re
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
    material_sources: dict[str, str]
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
    by_correlation_id: dict[str, list[ObservationRecord]] = {}
    for observation in observations:
        if observation.operation != "question_answer":
            continue
        by_correlation_id.setdefault(observation.correlation_id, []).append(observation)

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
        request_id = _text(question.get("request_id"), fallback="not_recorded")
        observation_matches = by_correlation_id.get(correlation_id, [])
        observation = _select_observation(
            matches=observation_matches,
            request_id=request_id,
        )
        expected = _dict(question.get("expected"))
        observed = _dict(question.get("observed"))
        rule_check = _dict(question.get("rule_check"))
        answer_projection = _step_facts(observation, "answer_projection")
        product_answer_items = _list(observed.get("answer_items")) or _list(
            answer_projection.get("items")
        )
        material_sources = _material_sources(run)

        reports.append(
            QuestionReport(
                id=_text(question.get("id"), fallback=f"question-{index}"),
                priority=_text(question.get("priority"), fallback="not_recorded"),
                question_text=_text(question.get("question")),
                correlation_id=correlation_id,
                request_id=request_id,
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
                material_sources=material_sources,
                observation=observation,
                observation_source=_observation_source_label(
                    observation=observation,
                    matches=observation_matches,
                    request_id=request_id,
                    run_dir=run_dir,
                ),
            )
        )
    return reports


def _select_observation(
    *,
    matches: list[ObservationRecord],
    request_id: str,
) -> ObservationRecord | None:
    if len(matches) == 1:
        return matches[0]
    request_matches = [
        observation for observation in matches if observation.request_id == request_id
    ]
    if len(request_matches) == 1:
        return request_matches[0]
    return None


def _observation_source_label(
    *,
    observation: ObservationRecord | None,
    matches: list[ObservationRecord],
    request_id: str,
    run_dir: Path,
) -> str:
    if observation is not None:
        return observation.relative_source(run_dir=run_dir)
    if not matches:
        return "not_found"
    request_match_count = sum(
        1 for observation_match in matches if observation_match.request_id == request_id
    )
    if request_match_count > 1:
        return (
            "ambiguous: "
            f"{request_match_count} observations matched correlation_id and request_id"
        )
    return f"ambiguous: {len(matches)} observations matched correlation_id"


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


def _material_sources(run: dict[str, Any]) -> dict[str, str]:
    requests = _dict(run.get("requests"))
    upload = _dict(requests.get("material_upload"))
    material_id = _text(upload.get("material_id"))
    dataset = _dict(run.get("dataset"))
    source = _text(dataset.get("material_text_file"))
    if not material_id or not source:
        return {}
    return {material_id: source}


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
            _metric("질문 수", summary.question_count),
            _metric("Rule check 통과", summary.passed_rule_checks),
            _metric("Rule check 실패", summary.failed_rule_checks),
            _metric("Request failures", summary.request_failures),
            _metric(
                "Expected evidence state",
                _compact_counts(summary.expected_state_counts),
            ),
            _metric(
                "Observed evidence state",
                _compact_counts(summary.observed_state_counts),
            ),
            "</div>",
            "</section>",
        ]
    )


def _render_question_table(questions: list[QuestionReport]) -> str:
    rows = "".join(
        "<tr>"
        f'<td><a href="#{_anchor(question.id)}">{_h(question.id)}</a>'
        f'<p class="question-snippet">{_h(question.question_text)}</p></td>'
        f"<td>{_h(question.priority)}</td>"
        f"<td>{_status_badge(question.expected_state)}</td>"
        f"<td>{_state_badges(question.observed_states)}</td>"
        f"<td>{_rule_badge(question.rule_passed)}</td>"
        f"<td>{_h(_list_label(question.missing_cues))}</td>"
        f"<td>{_h(_list_label(question.must_not_hits))}</td>"
        "</tr>"
        for question in questions
    )
    return "".join(
        [
            "<section>",
            "<h2>Question results</h2>",
            '<div class="table-wrap">',
            "<table>",
            "<thead><tr>",
            "<th>질문</th><th>Priority</th><th>Expected</th><th>Observed</th>",
            "<th>Rule check</th><th>빠진 근거 단서</th><th>금지 주장 감지</th>",
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
            f'<p class="question-lead">{_h(question.question_text or "question text not recorded")}</p>',
            _render_eval_verdict(question),
            _render_observation_trace(question),
            _render_evidence_path(question),
            '<details class="raw-facts">',
            "<summary>Raw details <span>ids, LangSmith hint, Answer projection facts</span></summary>",
            _render_trace_details(question),
            '<p class="section-help">아래 JSON은 product observation의 answer_projection facts입니다. eval expected/pass-fail은 run.json 쪽에만 있습니다.</p>',
            _render_json(question.answer_projection),
            "</details>",
            "</section>",
        ]
    )


def _render_eval_verdict(question: QuestionReport) -> str:
    return "".join(
        [
            '<section class="report-section eval-verdict">',
            '<p class="stage-kicker">Eval overlay</p>',
            "<h3>Eval verdict <span>run.json rule_check</span></h3>",
            '<p class="section-help">질문셋 기준으로 product response를 판정한 결과입니다. 이 영역은 observation trace가 아니라 eval run의 overlay입니다.</p>',
            '<div class="finding-grid">',
            '<div class="finding-card verdict-card">',
            "<h4>판정 요약 <span>Rule check</span></h4>",
            '<div class="outcome-line">',
            "<span>Expected</span>",
            _status_badge(question.expected_state),
            "<span>→ Observed</span>",
            _state_badges(question.observed_states),
            "</div>",
            '<div class="outcome-line">',
            "<span>Rule check</span>",
            _rule_badge(question.rule_passed),
            "<span>Product status</span>",
            _status_badge(question.product_status),
            "</div>",
            f'<p class="outcome-note">{_h(question.answer_summary or "summary not recorded")}</p>',
            _render_rule_summary(question),
            "</div>",
            '<div class="finding-card">',
            "<h4>제품이 사용자에게 돌려준 답 <span>Product answer</span></h4>",
            _render_answer_items(question.answer_items),
            "</div>",
            "</div>",
            "</section>",
        ]
    )


def _render_observation_trace(question: QuestionReport) -> str:
    steps = (
        _list(_dict(question.observation.payload).get("steps"))
        if question.observation
        else []
    )
    return "".join(
        [
            '<section class="report-section observation-trace">',
            '<p class="stage-kicker">Product runtime</p>',
            "<h3>Observation trace <span>product-owned step tree</span></h3>",
            '<p class="section-help">제품 실행 중 실제로 지나간 step tree입니다. 여기에는 eval expected, missing cue, pass/fail 판정이 들어가지 않습니다.</p>',
            _render_trace_tree(steps),
            "</section>",
        ]
    )


def _render_trace_tree(steps: list[Any]) -> str:
    if not steps:
        return '<p class="empty">No observation steps recorded.</p>'
    return (
        '<ol class="trace-tree">'
        + "".join(_render_trace_step(step) for step in steps)
        + "</ol>"
    )


def _render_trace_step(step: object) -> str:
    if not isinstance(step, dict):
        return ""
    name = _text(step.get("name"), fallback="unknown_step")
    status = _text(step.get("status"), fallback="unknown")
    facts = _dict(step.get("facts"))
    children = _list(step.get("children"))
    return "".join(
        [
            "<li>",
            '<div class="trace-step">',
            f"<strong>{_h(name)}</strong>",
            _status_badge(status),
            _render_fact_summary(facts),
            "</div>",
            _render_trace_tree(children) if children else "",
            "</li>",
        ]
    )


def _render_fact_summary(facts: dict[str, Any]) -> str:
    if not facts:
        return ""
    items = []
    for key, value in facts.items():
        items.append(
            "<span>"
            f"<b>{_h(key)}</b>: {_h(_fact_summary_value(key=key, value=value))}"
            "</span>"
        )
    return '<p class="fact-summary">' + "".join(items) + "</p>"


def _fact_summary_value(*, key: str, value: object) -> str:
    if key in {"candidates", "context_blocks", "items"} and isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, list):
        if len(value) <= 3:
            return ", ".join(str(item) for item in value)
        return f"{len(value)} item(s)"
    if isinstance(value, dict):
        return ", ".join(
            f"{item_key}: {item_value}" for item_key, item_value in value.items()
        )
    return str(value)


def _render_evidence_path(question: QuestionReport) -> str:
    return "".join(
        [
            '<section class="report-section evidence-path">',
            '<p class="stage-kicker">Data lineage</p>',
            "<h3>Evidence path <span>SourceUnit → Candidate → Context → AnswerItem → EvidenceRef</span></h3>",
            '<p class="section-help">source unit이 제품 답변의 evidenceRef까지 승격됐는지 보는 관점입니다. trace가 control flow라면, 이 영역은 data lineage입니다.</p>',
            _render_lineage_steps(question),
            _render_source_columns(question),
            "</section>",
        ]
    )


def _render_lineage_steps(question: QuestionReport) -> str:
    source_units = _source_unit_blocks(question.retrieval_candidates)
    evidence_refs = _answer_evidence_refs(question.answer_items)
    context_source_ids = {
        _text(block.get("source_unit_id"))
        for block in question.context_blocks
        if isinstance(block, dict)
    }
    candidate_used_count = sum(
        1
        for candidate in question.retrieval_candidates
        if isinstance(candidate, dict)
        and _text(candidate.get("source_unit_id")) in context_source_ids
    )
    return "".join(
        [
            '<ol class="lineage-steps">',
            _lineage_step(
                "SourceUnit",
                len(source_units),
                "retrieval candidates carry source units",
                _render_source_unit_details(
                    source_units=source_units,
                    material_sources=question.material_sources,
                ),
            ),
            _lineage_step(
                "Retrieval candidate",
                len(question.retrieval_candidates),
                "selected by retrieval",
                _render_retrieval_candidate_details(
                    candidates=question.retrieval_candidates,
                    context_source_ids=context_source_ids,
                    material_sources=question.material_sources,
                    highlight_terms=question.missing_cues,
                ),
            ),
            _lineage_step(
                "Composer context",
                len(question.context_blocks),
                f"{candidate_used_count} candidate id match; sent to answer composer",
                _render_context_block_details(
                    context_blocks=question.context_blocks,
                    material_sources=question.material_sources,
                    highlight_terms=question.missing_cues,
                ),
            ),
            _lineage_step(
                "Answer item",
                len(question.answer_items),
                _compact_counts(question.observed_states),
                _render_answer_item_details(question.answer_items),
            ),
            _lineage_step(
                "EvidenceRef",
                len(evidence_refs),
                "grounded snippet references",
                _render_evidence_ref_details(evidence_refs),
            ),
            "</ol>",
        ]
    )


def _lineage_step(label: str, count: int, note: str, details: str) -> str:
    state_class = "lineage-ok" if count > 0 else "lineage-missing"
    mark = "✓" if count > 0 else "×"
    return (
        f'<li class="{state_class}">'
        "<details>"
        "<summary>"
        f'<span class="lineage-mark">{_h(mark)}</span>'
        '<span class="lineage-summary-copy">'
        f"<strong>{_h(label)}</strong>"
        f"<span>{_h(count)} found · {_h(note)}</span>"
        "</span>"
        '<span class="lineage-toggle">펼쳐 보기</span>'
        "</summary>"
        f'<div class="lineage-details">{details}</div>'
        "</details>"
        "</li>"
    )


def _source_unit_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_units = []
    seen: set[str] = set()
    for block in blocks:
        source_unit_id = _text(block.get("source_unit_id"))
        if not source_unit_id or source_unit_id in seen:
            continue
        seen.add(source_unit_id)
        source_units.append(block)
    return source_units


def _answer_evidence_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        evidence
        for item in items
        if isinstance(item, dict)
        for evidence in _list(item.get("evidence"))
        if isinstance(evidence, dict)
    ]


def _render_source_unit_details(
    *,
    source_units: list[dict[str, Any]],
    material_sources: dict[str, str],
) -> str:
    if not source_units:
        return '<p class="empty">No SourceUnit reached retrieval.</p>'
    return "".join(
        _lineage_record(
            title=f"SourceUnit {index}",
            rows=[
                (
                    "source",
                    _source_label(
                        material_id=_text(source_unit.get("material_id")),
                        material_sources=material_sources,
                    ),
                ),
                (
                    "material_id",
                    _text(source_unit.get("material_id"), fallback="not recorded"),
                ),
                (
                    "source_unit_id",
                    _text(source_unit.get("source_unit_id"), fallback="not recorded"),
                ),
                (
                    "source location",
                    _text(source_unit.get("locator"), fallback="not recorded"),
                ),
                ("char_length", _int_or_text(source_unit.get("char_length"))),
                ("page", _int_or_text(source_unit.get("page"))),
                ("unit_index", _int_or_text(source_unit.get("unit_index"))),
            ],
            body_label="SourceUnit text",
            body=_text(source_unit.get("text")),
        )
        for index, source_unit in enumerate(source_units, start=1)
    )


def _render_retrieval_candidate_details(
    *,
    candidates: list[dict[str, Any]],
    context_source_ids: set[str],
    material_sources: dict[str, str],
    highlight_terms: list[str],
) -> str:
    if not candidates:
        return '<p class="empty">No retrieval candidates recorded.</p>'
    return "".join(
        _lineage_record(
            title=f"Candidate {index}",
            rows=[
                (
                    "source",
                    _source_label(
                        material_id=_text(candidate.get("material_id")),
                        material_sources=material_sources,
                    ),
                ),
                (
                    "material_id",
                    _text(candidate.get("material_id"), fallback="not recorded"),
                ),
                (
                    "source_unit_id",
                    _text(candidate.get("source_unit_id"), fallback="not recorded"),
                ),
                (
                    "source location",
                    _text(candidate.get("locator"), fallback="not recorded"),
                ),
                (
                    "sent_to_composer",
                    _yes_no(
                        _text(candidate.get("source_unit_id")) in context_source_ids
                    ),
                ),
                ("score", _score_or_text(candidate.get("score"))),
                ("vector_score", _score_or_text(candidate.get("vector_score"))),
                ("lexical_score", _score_or_text(candidate.get("lexical_score"))),
            ],
            body_label="후보 전문",
            body=_text(candidate.get("text")),
            highlight_terms=highlight_terms,
        )
        for index, candidate in enumerate(candidates, start=1)
    )


def _render_context_block_details(
    *,
    context_blocks: list[dict[str, Any]],
    material_sources: dict[str, str],
    highlight_terms: list[str],
) -> str:
    if not context_blocks:
        return '<p class="empty">No composer context blocks recorded.</p>'
    return "".join(
        _lineage_record(
            title=f"Context block {index}",
            rows=[
                (
                    "source",
                    _source_label(
                        material_id=_text(block.get("material_id")),
                        material_sources=material_sources,
                    ),
                ),
                (
                    "material_id",
                    _text(block.get("material_id"), fallback="not recorded"),
                ),
                (
                    "source_unit_id",
                    _text(block.get("source_unit_id"), fallback="not recorded"),
                ),
                (
                    "source location",
                    _text(block.get("locator"), fallback="not recorded"),
                ),
                ("char_length", _int_or_text(block.get("char_length"))),
            ],
            body_label="전달된 context 전문",
            body=_text(block.get("text")),
            highlight_terms=highlight_terms,
        )
        for index, block in enumerate(context_blocks, start=1)
    )


def _render_answer_item_details(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">No answer items recorded.</p>'
    return "".join(
        _lineage_record(
            title=_text(item.get("label"), fallback=f"Answer item {index}"),
            rows=[
                ("id", _text(item.get("id"), fallback="not recorded")),
                (
                    "evidence_state",
                    _text(item.get("evidence_state"), fallback="not recorded"),
                ),
                ("evidence_ref_count", len(_list(item.get("evidence")))),
                ("value", _text(item.get("value"), fallback="not recorded")),
            ],
            body_label="제품 답변 본문",
            body=_text(item.get("body")),
        )
        for index, item in enumerate(items, start=1)
    )


def _render_evidence_ref_details(evidence_refs: list[dict[str, Any]]) -> str:
    if not evidence_refs:
        return '<p class="empty">No EvidenceRef created for this run.</p>'
    return "".join(
        _lineage_record(
            title=f"EvidenceRef {index}",
            rows=[
                (
                    "source_unit_id",
                    _text(evidence.get("source_unit_id"), fallback="not recorded"),
                ),
                (
                    "source location",
                    _text(evidence.get("locator"), fallback="not recorded"),
                ),
            ],
            body_label="근거 snippet",
            body=_text(evidence.get("snippet")),
        )
        for index, evidence in enumerate(evidence_refs, start=1)
    )


def _lineage_record(
    *,
    title: str,
    rows: list[tuple[str, object]],
    body_label: str,
    body: str,
    highlight_terms: list[str] | None = None,
) -> str:
    body_html = ""
    if body:
        body_html = (
            f'<p class="text-label">{_h(body_label)}</p>'
            f'<pre class="lineage-text">{_highlighted_text(body, highlight_terms or [])}</pre>'
        )
    return (
        '<article class="lineage-record">'
        f"<h5>{_h(title)}</h5>"
        '<dl class="block-meta">'
        + "".join(_stat(label, value) for label, value in rows)
        + "</dl>"
        + body_html
        + "</article>"
    )


def _score_or_text(value: object) -> object:
    return value if isinstance(value, (int, float)) else "not recorded"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _render_outcome_panel(question: QuestionReport) -> str:
    return "".join(
        [
            '<article class="outcome-card">',
            "<h3>한눈에 보기</h3>",
            '<div class="outcome-line">',
            "<span>Expected</span>",
            _status_badge(question.expected_state),
            "<span>→ Observed</span>",
            _state_badges(question.observed_states),
            "</div>",
            '<div class="outcome-line">',
            "<span>Rule check</span>",
            _rule_badge(question.rule_passed),
            "<span>Product status</span>",
            _status_badge(question.product_status),
            "</div>",
            f'<p class="outcome-note">{_h(question.answer_summary or "summary not recorded")}</p>',
            "</article>",
        ]
    )


def _render_trace_details(question: QuestionReport) -> str:
    return "".join(
        [
            '<details class="trace-details">',
            "<summary>Trace ids and external viewer</summary>",
            '<dl class="meta-grid">',
            _stat("correlation_id", question.correlation_id),
            _stat("request_id", question.request_id),
            _stat("product_status", question.product_status),
            _stat("observation", question.observation_source),
            _stat("LangSmith hint", f"search correlation_id:{question.correlation_id}"),
            "</dl>",
            "</details>",
        ]
    )


def _render_rule_summary(question: QuestionReport) -> str:
    return "".join(
        [
            '<div class="rule-panel">',
            "<div>",
            "<strong>빠진 근거 단서</strong>",
            _render_term_list(question.missing_cues),
            "</div>",
            "<div>",
            "<strong>금지 주장 감지</strong>",
            _render_term_list(question.must_not_hits),
            "</div>",
            "</div>",
        ]
    )


def _render_term_list(values: list[str]) -> str:
    if not values:
        return '<p class="empty">none</p>'
    return "<ul>" + "".join(f"<li>{_h(value)}</li>" for value in values) + "</ul>"


def _render_evidence_flow(question: QuestionReport) -> str:
    return "".join(
        [
            '<ol class="flow-steps">',
            _flow_step(
                "1",
                "Retrieval",
                "candidate_summary",
                f"{len(question.retrieval_candidates)}개 후보",
            ),
            _flow_step(
                "2",
                "Context assembly",
                "context_assembly",
                f"{len(question.context_blocks)}개 context",
            ),
            _flow_step(
                "3",
                "Product answer",
                "answer_projection",
                _compact_counts(question.observed_states),
            ),
            _flow_step(
                "4",
                "Rule check",
                "run.json rule_check",
                _rule_label(question.rule_passed),
            ),
            "</ol>",
        ]
    )


def _flow_step(number: str, label: str, technical_name: str, value: str) -> str:
    return (
        "<li>"
        f'<span class="step-number">{_h(number)}</span>'
        "<div>"
        f"<strong>{_h(label)}</strong>"
        f"<code>{_h(technical_name)}</code>"
        f"<p>{_h(value)}</p>"
        "</div>"
        "</li>"
    )


def _render_source_columns(question: QuestionReport) -> str:
    context_source_ids = {
        _text(block.get("source_unit_id"))
        for block in question.context_blocks
        if isinstance(block, dict)
    }
    return "".join(
        [
            '<div class="source-grid">',
            '<section class="source-column">',
            '<p class="stage-kicker">Step 1 · Retrieval</p>',
            "<h4>검색된 근거 후보 <span>Retrieval candidates</span></h4>",
            '<p class="column-help">질문과 자료 범위를 바탕으로 retrieval이 먼저 찾아온 source unit입니다.</p>',
            _render_text_blocks(
                question.retrieval_candidates,
                kind="candidate",
                highlight_terms=question.missing_cues,
                context_source_ids=context_source_ids,
                material_sources=question.material_sources,
            ),
            "</section>",
            '<section class="source-column">',
            '<p class="stage-kicker">Step 2 · Context assembly</p>',
            "<h4>답변에 전달된 context <span>Composer context</span></h4>",
            '<p class="column-help">retrieval 후보 중 답변 생성 단계가 실제로 받은 context입니다.</p>',
            _render_text_blocks(
                question.context_blocks,
                kind="context",
                highlight_terms=question.missing_cues,
                material_sources=question.material_sources,
            ),
            "</section>",
            "</div>",
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


def _render_text_blocks(
    blocks: list[dict[str, Any]],
    *,
    kind: str,
    highlight_terms: list[str] | None = None,
    context_source_ids: set[str] | None = None,
    material_sources: dict[str, str] | None = None,
) -> str:
    if not blocks:
        return f'<p class="empty">No {kind} text recorded in observation.</p>'
    rendered = []
    for index, block in enumerate(blocks, start=1):
        score = block.get("score")
        score_text = (
            f"relevance score {score}" if isinstance(score, int | float) else ""
        )
        title = "Candidate" if kind == "candidate" else "Context block"
        text_label = "후보 전문" if kind == "candidate" else "전달된 context 전문"
        source_unit_id = _text(block.get("source_unit_id"), fallback="source_unit")
        material_id = _text(block.get("material_id"))
        source_label = _source_label(
            material_id=material_id,
            material_sources=material_sources or {},
        )
        is_used_as_context = (
            kind == "candidate"
            and context_source_ids is not None
            and source_unit_id in context_source_ids
        )
        rendered.append(
            "".join(
                [
                    '<article class="source-card">',
                    "<header>",
                    "<div>",
                    f"<strong>{_h(title)} {index}</strong>",
                    f"<p>{_h(_source_role_label(kind, is_used_as_context))}</p>",
                    "</div>",
                    '<div class="source-badges">',
                    f"<code>{_h(_text(block.get('locator'), fallback='locator'))}</code>",
                    f"<span>{_h(str(_int_or_text(block.get('char_length'))))} chars</span>",
                    f"<span>{_h(score_text)}</span>" if score_text else "",
                    (
                        '<span class="used-badge">sent to composer</span>'
                        if is_used_as_context
                        else ""
                    ),
                    "</div>",
                    "</header>",
                    f'<p class="source-title"><span>Source</span>{_h(source_label)}</p>',
                    '<dl class="block-meta">',
                    _stat("material_id", material_id or "not recorded"),
                    _stat("source_unit_id", source_unit_id),
                    _stat(
                        "source location",
                        _text(block.get("locator"), fallback="locator"),
                    ),
                    "</dl>",
                    f'<p class="text-label">{_h(text_label)}</p>',
                    f'<pre class="source-text">{_highlighted_text(_text(block.get("text"), fallback=""), highlight_terms or [])}</pre>',
                    "</article>",
                ]
            )
        )
    return "".join(rendered)


def _source_role_label(kind: str, is_used_as_context: bool) -> str:
    if kind == "context":
        return "답변 생성 단계에 실제로 전달됨"
    if is_used_as_context:
        return "검색 후보이며 context로도 전달됨"
    return "검색 후보"


def _source_label(*, material_id: str, material_sources: dict[str, str]) -> str:
    source = material_sources.get(material_id, "")
    if source:
        return source
    if material_id:
        return f"material {material_id}"
    return "source not recorded"


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


def _triage_tile(label: str, value: object) -> str:
    return (
        '<div class="triage-tile">'
        f"<span>{_h(label)}</span>"
        f"<strong>{_h(str(value))}</strong>"
        "</div>"
    )


def _rule_badge(value: bool | None) -> str:
    return _status_badge(_rule_label(value))


def _state_badges(counts: dict[str, int]) -> str:
    if not counts:
        return '<span class="muted">not recorded</span>'
    return " ".join(
        _status_badge(f"{key}: {value}") for key, value in sorted(counts.items())
    )


def _status_badge(label: str) -> str:
    return f'<span class="status {_status_class(label)}">{_h(label)}</span>'


def _status_class(label: str) -> str:
    normalized = label.lower()
    if any(
        token in normalized
        for token in ["passed", "supported", "accepted", "succeeded", "ready"]
    ):
        return "status-ok"
    if any(token in normalized for token in ["failed", "missing", "failure"]):
        return "status-bad"
    if "not recorded" in normalized or "unknown" in normalized:
        return "status-muted"
    return "status-neutral"


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
  max-width: 1320px;
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
h3 span {
  margin-left: 6px;
  color: #667085;
  font-size: 12px;
  font-weight: 600;
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
.finding-card,
.outcome-card,
.trace-details,
.source-card,
.raw-facts {
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
.investigation-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, .9fr);
  gap: 12px;
  margin: 14px 0 18px;
}
.outcome-card h3 {
  margin-top: 0;
}
.outcome-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
}
.outcome-line span {
  color: #667085;
  font-size: 12px;
  font-weight: 700;
}
.outcome-note {
  margin: 14px 0 0;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
  color: #334155;
  font-size: 15px;
  line-height: 1.55;
}
.trace-details {
  align-self: start;
}
.trace-details summary,
.raw-facts summary {
  cursor: pointer;
  font-weight: 700;
}
.trace-details .meta-grid {
  grid-template-columns: minmax(120px, max-content) minmax(0, 1fr);
  margin-top: 12px;
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
  min-width: 920px;
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
.question-snippet {
  margin: 6px 0 0;
  color: #334155;
  line-height: 1.45;
}
.question-detail {
  padding-top: 8px;
  border-top: 1px solid #d8dee4;
}
.question-lead {
  margin: -4px 0 0;
  color: #334155;
  font-size: 18px;
  line-height: 1.5;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 16px;
  margin-top: 18px;
}
.finding-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.finding-card h3 {
  margin-top: 0;
}
.stage-kicker {
  margin: 0 0 6px;
  color: #52616f;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}
.report-section {
  margin-top: 18px;
  border: 1px solid #d8dee4;
  border-radius: 8px;
  background: #fff;
  padding: 16px;
}
.report-section h3 {
  margin-top: 0;
}
.detail-block {
  margin-top: 24px;
}
.section-help {
  max-width: 980px;
  margin: 0 0 12px;
  color: #52616f;
  line-height: 1.55;
}
.answer-item,
.source-card {
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
.status {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  margin: 2px 4px 2px 0;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #d8dee4;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.status-ok {
  background: #edf7ee;
  border-color: #b7dfbd;
  color: #1f6b35;
}
.status-bad {
  background: #fff1f0;
  border-color: #ffc9c2;
  color: #b42318;
}
.status-neutral {
  background: #eef6ff;
  border-color: #c7dffd;
  color: #1d4f7a;
}
.status-muted {
  background: #f4f6f8;
  color: #5b6472;
}
.evidence-list {
  margin: 10px 0 0;
  padding-left: 20px;
}
.evidence-list blockquote {
  margin: 6px 0 0;
  color: #334155;
}
.flow-steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 16px;
  padding: 0;
  list-style: none;
}
.flow-steps li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid #d8dee4;
  border-radius: 8px;
  background: #fff;
}
.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  background: #1f2933;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex: 0 0 auto;
}
.flow-steps strong {
  display: block;
  font-size: 13px;
}
.flow-steps code {
  display: inline-block;
  margin-top: 5px;
}
.flow-steps p {
  margin: 3px 0 0;
  color: #52616f;
  font-size: 13px;
}
.trace-tree {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.trace-tree .trace-tree {
  margin-left: 20px;
  padding-left: 16px;
  border-left: 1px solid #d8dee4;
}
.trace-tree li {
  margin-top: 8px;
}
.trace-step {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fbfcfe;
}
.trace-step strong {
  min-width: 170px;
}
.fact-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0;
  color: #52616f;
  font-size: 12px;
}
.fact-summary span {
  border-radius: 999px;
  background: #eef2f6;
  padding: 2px 7px;
}
.lineage-steps {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  margin: 14px 0 16px;
  padding: 0;
  list-style: none;
}
.lineage-steps li {
  padding: 12px;
  border: 1px solid #d8dee4;
  border-radius: 8px;
  background: #fff;
}
.lineage-steps details {
  display: block;
}
.lineage-steps summary {
  display: flex;
  gap: 10px;
  align-items: center;
  cursor: pointer;
  list-style: none;
}
.lineage-steps summary::-webkit-details-marker {
  display: none;
}
.lineage-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  font-weight: 800;
  flex: 0 0 auto;
}
.lineage-ok .lineage-mark {
  background: #edf7ee;
  color: #1f6b35;
}
.lineage-missing .lineage-mark {
  background: #fff1f0;
  color: #b42318;
}
.lineage-summary-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-wrap: wrap;
  gap: 4px 10px;
  align-items: baseline;
}
.lineage-steps strong {
  display: block;
  font-size: 13px;
}
.lineage-summary-copy span {
  color: #52616f;
  font-size: 12px;
}
.lineage-toggle {
  border-radius: 999px;
  background: #eef2f6;
  color: #52616f;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 700;
}
.lineage-steps details[open] .lineage-toggle {
  background: #e8f1ff;
  color: #1d4f7a;
}
.lineage-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}
.lineage-record {
  margin-top: 10px;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fbfcfe;
}
.lineage-record:first-child {
  margin-top: 0;
}
.lineage-record h5 {
  margin: 0 0 8px;
  font-size: 13px;
}
.lineage-text {
  max-height: 220px;
  overflow: auto;
  font-size: 12px;
}
.source-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.source-column h4 {
  margin: 0;
}
.source-column h4 span {
  margin-left: 6px;
  color: #667085;
  font-size: 12px;
}
.column-help {
  margin: 6px 0 10px;
  color: #52616f;
  font-size: 13px;
}
.source-card {
  border-left: 4px solid #8ab4f8;
}
.source-column + .source-column .source-card {
  border-left-color: #8bd3b0;
}
.source-card header {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-start;
  color: #52616f;
  font-size: 12px;
}
.source-card header strong {
  display: block;
  color: #1f2933;
  font-size: 15px;
}
.source-card header p {
  margin: 3px 0 0;
}
.source-badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}
.source-badges span {
  border-radius: 999px;
  background: #eef2f6;
  padding: 2px 7px;
  font-size: 12px;
}
.source-badges .used-badge {
  background: #edf7ee;
  color: #1f6b35;
  font-weight: 700;
}
.source-title {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 6px;
  background: #f8fafc;
  color: #1f2933;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.source-title span {
  margin-right: 8px;
  color: #667085;
  font-size: 12px;
  text-transform: uppercase;
}
.block-meta {
  display: grid;
  grid-template-columns: minmax(120px, max-content) minmax(0, 1fr);
  gap: 4px 10px;
  margin-top: 10px;
}
.block-meta dd {
  margin-bottom: 0;
}
.text-label {
  margin: 12px 0 0;
  color: #667085;
  font-size: 12px;
  font-weight: 700;
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
  line-height: 1.5;
}
.source-text {
  max-height: 360px;
  overflow: auto;
  font-size: 12px;
}
.json {
  border: 1px solid #d8dee4;
}
.raw-facts {
  margin-top: 24px;
}
.rule-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}
.rule-panel > div {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fbfcfe;
  padding: 12px;
}
.rule-panel strong {
  display: block;
  margin-bottom: 8px;
}
.rule-panel ul {
  margin: 0;
  padding-left: 20px;
}
mark {
  background: #fff2a8;
  border-radius: 3px;
  padding: 0 2px;
}
.empty {
  color: #667085;
}
.muted {
  color: #667085;
}
@media (max-width: 980px) {
  .investigation-grid,
  .source-grid {
    grid-template-columns: 1fr;
  }
  .flow-steps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  main {
    padding: 24px 12px 48px;
  }
  .hero {
    display: block;
  }
  .finding-grid,
  .flow-steps,
  .lineage-steps {
    grid-template-columns: 1fr;
  }
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


def _highlighted_text(text: str, terms: list[str]) -> str:
    active_terms = sorted(
        {term for term in terms if term},
        key=len,
        reverse=True,
    )
    if not active_terms:
        return _h(text)

    pattern = re.compile("|".join(re.escape(term) for term in active_terms))
    rendered = []
    cursor = 0
    for match in pattern.finditer(text):
        rendered.append(_h(text[cursor : match.start()]))
        rendered.append(f"<mark>{_h(match.group(0))}</mark>")
        cursor = match.end()
    rendered.append(_h(text[cursor:]))
    return "".join(rendered)


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
