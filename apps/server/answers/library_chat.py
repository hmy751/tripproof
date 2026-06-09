from __future__ import annotations

import re
from typing import Protocol

from server.core.config import (
    FACT_PROPOSER_BACKEND,
    OLLAMA_BASE_URL,
    OLLAMA_FACT_MODEL,
    OLLAMA_FACT_TIMEOUT_SECONDS,
)
from server.extraction.evidence import EvidenceGroundingError, evidence_ref_from_snippet
from server.extraction.models import EvidenceRef, EvidenceState
from server.llm.ollama import OllamaChatJsonClient, OllamaChatJsonConfig, OllamaClientError
from server.retrieval.models import ContextPack, SourceUnit
from server.schemas.answers import ChatAnswerItemResponse, ChatAnswerResponse
from server.schemas.facts import EvidenceRefResponse


LIBRARY_CHAT_TARGET_ID = "library_chat_answer"


class LibraryChatAnswerComposer(Protocol):
    def compose(self, *, question: str, context: ContextPack) -> ChatAnswerResponse:
        """Build a user-facing answer from retrieved source units."""


class MissingLibraryChatAnswerComposer:
    def __init__(self, *, reason: str = "답변 생성기가 비활성화되어 있습니다.") -> None:
        self._reason = reason

    def compose(self, *, question: str, context: ContextPack) -> ChatAnswerResponse:
        return _missing_answer(reason=self._reason)


class OllamaLibraryChatAnswerComposer:
    def __init__(self, *, client: OllamaChatJsonClient) -> None:
        self._client = client

    def compose(self, *, question: str, context: ContextPack) -> ChatAnswerResponse:
        if not context.candidates:
            return _missing_answer(reason="질문과 관련된 source unit 후보를 찾지 못했습니다.")

        try:
            payload = self._client.generate_json(
                system=_system_prompt(),
                user=_user_prompt(question=question, context=context),
            )
        except OllamaClientError as exc:
            return _missing_answer(reason=f"답변 생성에 실패했습니다: {exc}")

        return _answer_from_payload(question=question, payload=payload, context=context)


def create_library_chat_answer_composer_from_config(
    *,
    backend: str | None = None,
) -> LibraryChatAnswerComposer:
    active_backend = (backend or FACT_PROPOSER_BACKEND).lower()
    if active_backend == "ollama":
        return OllamaLibraryChatAnswerComposer(
            client=OllamaChatJsonClient(
                OllamaChatJsonConfig(
                    base_url=OLLAMA_BASE_URL,
                    model=OLLAMA_FACT_MODEL,
                    timeout_seconds=OLLAMA_FACT_TIMEOUT_SECONDS,
                )
            )
        )
    if active_backend in {"disabled", "missing"}:
        return MissingLibraryChatAnswerComposer()
    raise ValueError(f"Unsupported library chat answer backend: {active_backend}")


def _system_prompt() -> str:
    return (
        "You answer questions about the user's travel materials. "
        "Use only the provided source unit text. Do not infer from general travel knowledge. "
        "If the source units do not support an answer, say it is missing. "
        "Return JSON only."
    )


def _user_prompt(*, question: str, context: ContextPack) -> str:
    source_blocks = "\n\n".join(
        (
            f"source_unit_id: {candidate.source_unit.id}\n"
            f"locator: {candidate.source_unit.locator}\n"
            f"text:\n{candidate.source_unit.text}"
        )
        for candidate in context.candidates
    )
    return (
        f"question: {question}\n\n"
        "Answer the question directly in Korean.\n"
        "Return this JSON shape exactly:\n"
        "{\n"
        '  "items": [\n'
        "    {\n"
        '      "id": "short_snake_case_or_null",\n'
        '      "label": "short Korean label",\n'
        '      "body": "Korean answer sentence",\n'
        '      "value": "string or null",\n'
        '      "evidence_state": "supported | missing | needs_review",\n'
        '      "source_unit_id": "string or null",\n'
        '      "evidence_snippet": "string or null"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- If an item is supported, source_unit_id must be one of the provided ids.\n"
        "- If an item is supported, evidence_snippet must be an exact substring copied from that source unit text.\n"
        "- If the exact source text does not support the answer, use evidence_state missing and value null.\n"
        "- Do not answer a different checklist item just because it is present in the source.\n\n"
        "Writing rules:\n"
        "- label is the requested field name, not the answer value. For example: 체크인 날짜, 체크인 시작 시각, 결제 수단.\n"
        "- body must be a complete Korean sentence that directly answers the user's question.\n"
        "- id must not be a source_unit_id. Use answer or a short semantic snake_case id.\n\n"
        f"Retrieved source units:\n{source_blocks}"
    )


def _answer_from_payload(*, question: str, payload: object, context: ContextPack) -> ChatAnswerResponse:
    if not isinstance(payload, dict):
        return _missing_answer(reason="답변 생성기가 JSON object를 반환하지 않았습니다.")

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return _missing_answer(reason="답변 생성기가 answer item을 반환하지 않았습니다.")

    items = [
        item
        for index, raw_item in enumerate(raw_items, start=1)
        if (item := _item_from_payload(index=index, question=question, payload=raw_item, context=context)) is not None
    ]
    if not items:
        return _missing_answer(reason="답변 생성기가 검증 가능한 answer item을 반환하지 않았습니다.")

    return ChatAnswerResponse(summary=_summary_for_items(items), items=items)


def _item_from_payload(
    *,
    index: int,
    question: str,
    payload: object,
    context: ContextPack,
) -> ChatAnswerItemResponse | None:
    if not isinstance(payload, dict):
        return None

    evidence_state = _evidence_state_from_value(_field(payload, "evidence_state", "evidenceState"))
    raw_label = _optional_string(_field(payload, "label"))
    body = _optional_string(_field(payload, "body")) or ""
    value = _optional_string(_field(payload, "value"))
    label = _display_label(raw_label=raw_label, value=value)
    body = _display_body(question=question, label=label, body=body, value=value)

    if evidence_state == EvidenceState.SUPPORTED:
        source_unit_id = _optional_string(_field(payload, "source_unit_id", "sourceUnitId"))
        evidence_snippet = _optional_string(_field(payload, "evidence_snippet", "evidenceSnippet"))
        if not body or source_unit_id is None or evidence_snippet is None:
            return _ungrounded_item(index=index, label=label)
        if not _supported_value_matches_question(question=question, value=value, body=body):
            return _ungrounded_item(index=index, label=label)

        source_unit = _source_unit_by_id(context=context, source_unit_id=source_unit_id)
        if source_unit is None:
            return _ungrounded_item(index=index, label=label)

        try:
            evidence_ref = evidence_ref_from_snippet(source_unit=source_unit, snippet=evidence_snippet)
        except EvidenceGroundingError:
            evidence_ref = _evidence_ref_from_value(source_unit=source_unit, value=value)
            if evidence_ref is None:
                return _ungrounded_item(index=index, label=label)

        return ChatAnswerItemResponse(
            id=_item_id(payload=payload, index=index),
            label=label,
            body=body,
            evidence_state=EvidenceState.SUPPORTED,
            value=value,
            evidence=[EvidenceRefResponse.from_domain(evidence_ref)],
        )

    if evidence_state == EvidenceState.NEEDS_REVIEW:
        return ChatAnswerItemResponse(
            id=_item_id(payload=payload, index=index),
            label=label,
            body=body or f"{label}은 원문 확인이 필요합니다.",
            evidence_state=EvidenceState.NEEDS_REVIEW,
            value=value,
            evidence=[],
        )

    return ChatAnswerItemResponse(
        id=_item_id(payload=payload, index=index),
        label=label,
        body=body or f"현재 등록된 자료에서 {label}을 확인하지 못했습니다.",
        evidence_state=EvidenceState.MISSING,
        value=None,
        evidence=[],
    )


def _summary_for_items(items: list[ChatAnswerItemResponse]) -> str:
    supported_count = sum(item.evidence_state == EvidenceState.SUPPORTED for item in items)
    missing_count = sum(item.evidence_state == EvidenceState.MISSING for item in items)
    if supported_count and missing_count:
        return "자료에서 확인한 내용과 확인되지 않은 항목입니다."
    if supported_count:
        return "자료에서 확인한 답변입니다."
    return "현재 등록된 자료만으로는 답을 확인하지 못했습니다."


def _missing_answer(*, reason: str) -> ChatAnswerResponse:
    return ChatAnswerResponse(
        summary="현재 등록된 자료만으로는 답을 확인하지 못했습니다.",
        items=[
            ChatAnswerItemResponse(
                id="answer",
                label="답변",
                body="현재 등록된 자료에서 질문에 대한 답을 확인하지 못했습니다.",
                evidence_state=EvidenceState.MISSING,
                value=None,
                evidence=[],
            )
        ],
    )


def _ungrounded_item(*, index: int, label: str) -> ChatAnswerItemResponse:
    return ChatAnswerItemResponse(
        id=f"answer_{index}",
        label=label,
        body=f"현재 등록된 자료에서 {label}의 근거를 확인하지 못했습니다.",
        evidence_state=EvidenceState.MISSING,
        value=None,
        evidence=[],
    )


def _source_unit_by_id(*, context: ContextPack, source_unit_id: str) -> SourceUnit | None:
    for candidate in context.candidates:
        if candidate.source_unit.id == source_unit_id:
            return candidate.source_unit
    return None


def _evidence_ref_from_value(*, source_unit: SourceUnit, value: str | None) -> EvidenceRef | None:
    if value is None:
        return None

    try:
        return evidence_ref_from_snippet(source_unit=source_unit, snippet=value)
    except EvidenceGroundingError:
        pass

    snippet = _numeric_value_window(source_text=source_unit.text, value=value)
    if snippet is None:
        return None

    try:
        return evidence_ref_from_snippet(source_unit=source_unit, snippet=snippet)
    except EvidenceGroundingError:
        return None


def _numeric_value_window(*, source_text: str, value: str) -> str | None:
    value_numbers = re.findall(r"\d+", value)
    if not value_numbers:
        return None

    source_numbers = list(re.finditer(r"\d+", source_text))
    if not source_numbers:
        return None

    normalized_value_numbers = [_normalize_number(number) for number in value_numbers]
    source_index = 0
    matched = []
    for value_number in normalized_value_numbers:
        while source_index < len(source_numbers):
            candidate = source_numbers[source_index]
            source_index += 1
            if _normalize_number(candidate.group(0)) == value_number:
                matched.append(candidate)
                break
        else:
            return None

    first = matched[0]
    last = matched[-1]
    if last.end() - first.start() > 220:
        return None

    window_start = _numeric_value_window_start(source_text=source_text, start=first.start())
    window_end = _numeric_value_window_end(source_text=source_text, end=last.end())
    return source_text[window_start:window_end].strip()


def _numeric_value_window_start(*, source_text: str, start: int) -> int:
    fallback_start = max(0, start - 80)
    position = start
    for _line in range(4):
        previous_break = source_text.rfind("\n", 0, position)
        if previous_break < 0:
            return fallback_start
        position = previous_break
    return max(fallback_start, position + 1)


def _numeric_value_window_end(*, source_text: str, end: int) -> int:
    position = end
    unit_chars = set("년월일시분초원엔박명개")
    while position < len(source_text) and position - end < 24:
        char = source_text[position]
        if char.isspace() or char in unit_chars:
            position += 1
            continue
        break
    return position


def _normalize_number(value: str) -> str:
    stripped = value.lstrip("0")
    return stripped or "0"


def _supported_value_matches_question(*, question: str, value: str | None, body: str) -> bool:
    if not _question_asks_time(question):
        return True
    answer_text = value or body
    return _looks_like_time_answer(answer_text)


def _question_asks_time(question: str) -> bool:
    normalized = question.lower()
    return any(
        term in normalized
        for term in (
            "몇 시",
            "몇시",
            "시간",
            "시각",
            "시작",
            "부터",
            "time",
            "start",
            "starts",
            "from",
        )
    )


def _looks_like_time_answer(value: str) -> bool:
    normalized = value.lower()
    return bool(
        re.search(r"\b\d{1,2}:\d{2}\b", normalized)
        or re.search(r"\b(am|pm)\b", normalized)
        or re.search(r"(오전|오후)\s*\d{1,2}\s*시", normalized)
        or re.search(r"\d{1,2}\s*시", normalized)
    )


def _item_id(*, payload: dict[object, object], index: int) -> str:
    value = _optional_string(_field(payload, "id"))
    if value is None:
        return f"answer_{index}"
    if value.startswith("su_"):
        return f"answer_{index}"
    normalized = "".join(char if char.isalnum() or char == "_" else "_" for char in value.strip().lower())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized or f"answer_{index}"


def _display_label(*, raw_label: str | None, value: str | None) -> str:
    if raw_label is None:
        return "답변"
    normalized_label = " ".join(raw_label.split())
    normalized_value = " ".join((value or "").split())
    if normalized_value and normalized_label == normalized_value:
        return "답변"
    if normalized_label.startswith("su_"):
        return "답변"
    return normalized_label or "답변"


def _display_body(*, question: str, label: str, body: str, value: str | None) -> str:
    normalized_body = " ".join(body.split())
    normalized_value = " ".join((value or "").split())
    if normalized_value and normalized_body == normalized_value:
        subject = _question_subject(question)
        if subject:
            return f"{subject}: {normalized_value}"
        if label != "답변":
            return f"{label}: {normalized_value}"
        return f"자료에서 확인한 내용은 {normalized_value}입니다."
    return normalized_body


def _question_subject(question: str) -> str | None:
    stripped = question.strip().rstrip("?!.。")
    for suffix in (
        "가 어떻게 돼",
        "이 어떻게 돼",
        "은 어떻게 돼",
        "는 어떻게 돼",
        " 어떻게 돼",
        "가 뭐야",
        "이 뭐야",
        "은 뭐야",
        "는 뭐야",
        " 뭐야",
    ):
        if stripped.endswith(suffix):
            subject = stripped[: -len(suffix)].strip()
            return subject or None
    return None


def _evidence_state_from_value(value: object) -> EvidenceState:
    if not isinstance(value, str):
        return EvidenceState.MISSING
    try:
        return EvidenceState(value.strip().lower())
    except ValueError:
        return EvidenceState.MISSING


def _field(payload: dict[object, object], *names: str) -> object:
    for name in names:
        if name in payload:
            return payload[name]
    return None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    stripped = value.strip()
    if not stripped or stripped.lower() == "null":
        return None
    return stripped
