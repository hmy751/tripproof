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
from server.answers.library_chat_payload import (
    NormalizedAnswerItemPayload,
    normalize_answer_item_payload,
)
from server.answers.models import ChatAnswer, ChatAnswerItem
from server.llm.ollama import (
    OllamaChatJsonClient,
    OllamaChatJsonConfig,
    OllamaClientError,
)
from server.prompts.renderers.answer.library_chat_answer import (
    LibraryChatAnswerPrompt,
    load_library_chat_answer_prompt,
)
from server.retrieval.models import AnswerContext, SourceUnit

LIBRARY_CHAT_TARGET_ID = "library_chat_answer"


class LibraryChatAnswerComposer(Protocol):
    def compose(self, *, question: str, context: AnswerContext) -> ChatAnswer:
        """Build a user-facing answer from retrieved source units."""


class MissingLibraryChatAnswerComposer:
    def __init__(
        self,
        *,
        reason: str = "답변 생성기가 비활성화되어 있습니다.",
        backend: str = "missing",
    ) -> None:
        self._reason = reason
        self._backend = backend

    def compose(self, *, question: str, context: AnswerContext) -> ChatAnswer:
        return _missing_answer(reason=self._reason)

    def runtime_answer_model_snapshot(self) -> dict[str, str | None]:
        return {
            "backend": self._backend,
            "model": None,
        }


class OllamaLibraryChatAnswerComposer:
    def __init__(
        self,
        *,
        client: OllamaChatJsonClient,
        prompt: LibraryChatAnswerPrompt | None = None,
        model: str | None = None,
    ) -> None:
        self._client = client
        self._prompt = prompt or load_library_chat_answer_prompt()
        self._model = model

    @property
    def prompt(self) -> LibraryChatAnswerPrompt:
        return self._prompt

    def compose(self, *, question: str, context: AnswerContext) -> ChatAnswer:
        if not context.candidates:
            return _missing_answer(
                reason="질문과 관련된 source unit 후보를 찾지 못했습니다."
            )

        try:
            payload = self._client.generate_json(
                system=self._prompt.system_message(),
                user=_user_prompt(
                    question=question, context=context, prompt=self._prompt
                ),
            )
        except OllamaClientError as exc:
            return _missing_answer(reason=f"답변 생성에 실패했습니다: {exc}")

        return _answer_from_payload(question=question, payload=payload, context=context)

    def runtime_answer_model_snapshot(self) -> dict[str, str | None]:
        return {
            "backend": "ollama",
            "model": self._model,
        }


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
            ),
            model=OLLAMA_FACT_MODEL,
        )
    if active_backend in {"disabled", "missing"}:
        return MissingLibraryChatAnswerComposer(backend=active_backend)
    raise ValueError(f"Unsupported library chat answer backend: {active_backend}")


def _user_prompt(
    *, question: str, context: AnswerContext, prompt: LibraryChatAnswerPrompt
) -> str:
    source_blocks = "\n\n".join(
        (
            f"source_unit_id: {candidate.source_unit.id}\n"
            f"locator: {candidate.source_unit.locator}\n"
            f"text:\n{candidate.source_unit.text}"
        )
        for candidate in context.candidates
    )
    return prompt.user_message(question=question, source_blocks=source_blocks)


def _answer_from_payload(
    *, question: str, payload: object, context: AnswerContext
) -> ChatAnswer:
    if not isinstance(payload, dict):
        return _missing_answer(
            reason="답변 생성기가 JSON object를 반환하지 않았습니다."
        )

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return _missing_answer(
            reason="답변 생성기가 answer item을 반환하지 않았습니다."
        )

    items = [
        item
        for index, raw_item in enumerate(raw_items, start=1)
        if (
            item := _item_from_payload(
                index=index, question=question, payload=raw_item, context=context
            )
        )
        is not None
    ]
    if not items:
        return _missing_answer(
            reason="답변 생성기가 검증 가능한 answer item을 반환하지 않았습니다."
        )

    return ChatAnswer(summary=_summary_for_items(items), items=items)


def _item_from_payload(
    *,
    index: int,
    question: str,
    payload: object,
    context: AnswerContext,
) -> ChatAnswerItem | None:
    item_payload = normalize_answer_item_payload(question=question, payload=payload)
    if item_payload is None:
        return None

    if item_payload.evidence_state == EvidenceState.SUPPORTED:
        return _supported_item_from_payload(
            index=index,
            question=question,
            payload=item_payload,
            context=context,
        )

    if item_payload.evidence_state == EvidenceState.NEEDS_REVIEW:
        return _needs_review_item_from_payload(
            index=index,
            payload=item_payload,
        )

    return _missing_item_from_payload(
        index=index,
        payload=item_payload,
    )


def _supported_item_from_payload(
    *,
    index: int,
    question: str,
    payload: NormalizedAnswerItemPayload,
    context: AnswerContext,
) -> ChatAnswerItem:
    if (
        not payload.body
        or payload.source_unit_id is None
        or payload.evidence_snippet is None
    ):
        return _ungrounded_item(index=index, label=payload.label)
    if not _supported_value_matches_question(
        question=question, value=payload.value, body=payload.body
    ):
        return _ungrounded_item(index=index, label=payload.label)

    source_unit = _source_unit_by_id(
        context=context, source_unit_id=payload.source_unit_id
    )
    if source_unit is None:
        return _ungrounded_item(index=index, label=payload.label)

    evidence_ref = _ground_evidence_ref(
        source_unit=source_unit,
        evidence_snippet=payload.evidence_snippet,
        value=payload.value,
    )
    if evidence_ref is None:
        return _ungrounded_item(index=index, label=payload.label)

    return ChatAnswerItem(
        id=payload.response_id(index=index),
        label=payload.label,
        body=payload.body,
        evidence_state=EvidenceState.SUPPORTED,
        value=payload.value,
        evidence=[evidence_ref],
    )


def _needs_review_item_from_payload(
    *,
    index: int,
    payload: NormalizedAnswerItemPayload,
) -> ChatAnswerItem:
    return ChatAnswerItem(
        id=payload.response_id(index=index),
        label=payload.label,
        body=payload.body or f"{payload.label}은 원문 확인이 필요합니다.",
        evidence_state=EvidenceState.NEEDS_REVIEW,
        value=payload.value,
        evidence=[],
    )


def _missing_item_from_payload(
    *,
    index: int,
    payload: NormalizedAnswerItemPayload,
) -> ChatAnswerItem:
    return ChatAnswerItem(
        id=payload.response_id(index=index),
        label=payload.label,
        body=payload.body
        or f"현재 등록된 자료에서 {payload.label}을 확인하지 못했습니다.",
        evidence_state=EvidenceState.MISSING,
        value=None,
        evidence=[],
    )


def _ground_evidence_ref(
    *,
    source_unit: SourceUnit,
    evidence_snippet: str,
    value: str | None,
) -> EvidenceRef | None:
    try:
        return evidence_ref_from_snippet(
            source_unit=source_unit, snippet=evidence_snippet
        )
    except EvidenceGroundingError:
        return _evidence_ref_from_value(source_unit=source_unit, value=value)


def _summary_for_items(items: list[ChatAnswerItem]) -> str:
    supported_count = sum(
        item.evidence_state == EvidenceState.SUPPORTED for item in items
    )
    missing_count = sum(item.evidence_state == EvidenceState.MISSING for item in items)
    if supported_count and missing_count:
        return "자료에서 확인한 내용과 확인되지 않은 항목입니다."
    if supported_count:
        return "자료에서 확인한 답변입니다."
    return "현재 등록된 자료만으로는 답을 확인하지 못했습니다."


def _missing_answer(*, reason: str) -> ChatAnswer:
    return ChatAnswer(
        summary="현재 등록된 자료만으로는 답을 확인하지 못했습니다.",
        items=[
            ChatAnswerItem(
                id="answer",
                label="답변",
                body="현재 등록된 자료에서 질문에 대한 답을 확인하지 못했습니다.",
                evidence_state=EvidenceState.MISSING,
                value=None,
                evidence=[],
            )
        ],
    )


def _ungrounded_item(*, index: int, label: str) -> ChatAnswerItem:
    return ChatAnswerItem(
        id=f"answer_{index}",
        label=label,
        body=f"현재 등록된 자료에서 {label}의 근거를 확인하지 못했습니다.",
        evidence_state=EvidenceState.MISSING,
        value=None,
        evidence=[],
    )


def _source_unit_by_id(
    *, context: AnswerContext, source_unit_id: str
) -> SourceUnit | None:
    for candidate in context.candidates:
        if candidate.source_unit.id == source_unit_id:
            return candidate.source_unit
    return None


def _evidence_ref_from_value(
    *, source_unit: SourceUnit, value: str | None
) -> EvidenceRef | None:
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

    window_start = _numeric_value_window_start(
        source_text=source_text, start=first.start()
    )
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


def _supported_value_matches_question(
    *, question: str, value: str | None, body: str
) -> bool:
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
