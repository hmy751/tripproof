from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from server.core.config import (
    OLLAMA_ANSWER_SEED,
    OLLAMA_ANSWER_MODEL,
    OLLAMA_ANSWER_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
)
from server.answers.candidate import AnswerCandidate, answer_candidate_from_payload
from server.answers.certification import certify
from server.answers.models import ChatAnswer, ChatAnswerItem
from server.answers.relation import (
    GoverningConditionExtractor,
    create_governing_condition_extractor_from_config,
)
from server.extraction.models import Certification, EvidenceState
from server.llm.ollama import (
    OllamaChatJsonClient,
    OllamaChatJsonConfig,
    OllamaClientError,
)
from server.prompts.renderers.answer.library_chat_answer import (
    LibraryChatAnswerPrompt,
    load_library_chat_answer_prompt,
)
from server.retrieval.models import AnswerContext

LIBRARY_CHAT_TARGET_ID = "library_chat_answer"


# ── Composer interface & implementations ────────────────────────────────────
class LibraryChatAnswerComposer(Protocol):
    def compose(self, *, question: str, context: AnswerContext) -> ChatAnswer:
        """Build a user-facing answer from retrieved source units."""


class OllamaLibraryChatAnswerComposer:
    def __init__(
        self,
        *,
        client: OllamaChatJsonClient,
        prompt: LibraryChatAnswerPrompt | None = None,
        model: str | None = None,
        seed: int | None = None,
        temperature: float | None = 0.0,
        relation_extractor: GoverningConditionExtractor | None = None,
    ) -> None:
        self._client = client
        self._prompt = prompt or load_library_chat_answer_prompt()
        self._model = model
        self._seed = seed
        self._temperature = temperature
        self._relation_extractor = relation_extractor

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
                user=_format_source_blocks(
                    question=question, context=context, prompt=self._prompt
                ),
            )
        except OllamaClientError as exc:
            return _missing_answer(reason=f"답변 생성에 실패했습니다: {exc}")

        return _answer_from_payload(
            question=question,
            payload=payload,
            context=context,
            relation_extractor=self._relation_extractor,
        )

    def runtime_answer_model_snapshot(self) -> dict[str, object]:
        return {
            "backend": "ollama",
            "model": self._model,
            "seed": self._seed,
            "temperature": self._temperature,
        }


def create_library_chat_answer_composer_from_config(
    *, answer_seed: int | None = None
) -> LibraryChatAnswerComposer:
    seed = OLLAMA_ANSWER_SEED if answer_seed is None else answer_seed
    return OllamaLibraryChatAnswerComposer(
        client=OllamaChatJsonClient(
            OllamaChatJsonConfig(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_ANSWER_MODEL,
                timeout_seconds=OLLAMA_ANSWER_TIMEOUT_SECONDS,
                seed=seed,
            )
        ),
        model=OLLAMA_ANSWER_MODEL,
        seed=seed,
        temperature=0.0,
        relation_extractor=create_governing_condition_extractor_from_config(
            answer_seed=seed
        ),
    )


# ── Prompt assembly ─────────────────────────────────────────────────────────
def _format_source_blocks(
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


# ── Payload → candidate → certification → final item ────────────────────────
def _answer_from_payload(
    *,
    question: str,
    payload: object,
    context: AnswerContext,
    relation_extractor: GoverningConditionExtractor | None = None,
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

    items: list[ChatAnswerItem] = []
    for index, raw_item in enumerate(raw_items, start=1):
        candidate = answer_candidate_from_payload(
            index=index, question=question, payload=raw_item
        )
        if candidate is None:
            continue
        candidate = _enrich_with_governing_condition(
            question=question,
            candidate=candidate,
            context=context,
            relation_extractor=relation_extractor,
        )
        certification = certify(candidate=candidate, context=context)
        items.append(
            _item_from_certification(candidate=candidate, certification=certification)
        )

    if not items:
        return _missing_answer(
            reason="답변 생성기가 검증 가능한 answer item을 반환하지 않았습니다."
        )

    return ChatAnswer(summary=_summary_for_items(items), items=items)


def _enrich_with_governing_condition(
    *,
    question: str,
    candidate: AnswerCandidate,
    context: AnswerContext,
    relation_extractor: GoverningConditionExtractor | None,
) -> AnswerCandidate:
    """별도 relation pass로 '값을 좌우하는 조건' 역할을 채운다(06 robust fix).

    답변 호출이 supported를 제안했는데 governing_condition을 안 채운 경우에만, 답을 쓴
    호출과 분리된 두 번째 호출로 조건만 따로 묻는다(생성/검증 분리). supported가 아니거나
    이미 조건이 있으면 두 번째 호출을 아끼고 그대로 둔다. certify가 그 결과를 읽어
    grounding되면 강등한다 — 코드는 의미를 분류하지 않는다.
    """

    if relation_extractor is None:
        return candidate
    if candidate.proposed_state != EvidenceState.SUPPORTED:
        return candidate
    if candidate.governing_condition is not None:
        return candidate
    governing = relation_extractor.extract(
        question=question, candidate=candidate, context=context
    )
    if governing is None:
        return candidate
    return replace(candidate, governing_condition=governing)


def _item_from_certification(
    *, candidate: AnswerCandidate, certification: Certification
) -> ChatAnswerItem:
    item_id = candidate.item_id()
    if certification.state == EvidenceState.SUPPORTED:
        return ChatAnswerItem(
            id=item_id,
            label=candidate.label,
            body=_supported_body(candidate),
            evidence_state=EvidenceState.SUPPORTED,
            value=candidate.value,
            evidence=list(certification.evidence),
            certification=certification,
        )

    if certification.state == EvidenceState.NEEDS_REVIEW:
        return ChatAnswerItem(
            id=item_id,
            label=candidate.label,
            body=_needs_review_body(candidate=candidate, certification=certification),
            evidence_state=EvidenceState.NEEDS_REVIEW,
            value=candidate.value,
            evidence=list(certification.evidence),
            certification=certification,
        )

    return ChatAnswerItem(
        id=item_id,
        label=candidate.label,
        body=_missing_body(candidate=candidate, certification=certification),
        evidence_state=EvidenceState.MISSING,
        value=None,
        evidence=[],
        certification=certification,
    )


# ── Final body rendering (certified state 뒤에서만 생성) ─────────────────────
# body는 certification 결과를 풀어 쓰는 마지막 단계다. state를 승격하거나 새 값을
# 만들 수 없고, certified state를 거슬러 "확정"처럼 말할 수 없다(AC5). needs_review/
# missing body는 LLM draft를 쓰지 않고 코드 template으로 만들어 overclaim을 막는다.
def _supported_body(candidate: AnswerCandidate) -> str:
    if candidate.draft_body:
        return candidate.draft_body
    if candidate.value:
        return f"{candidate.label}: {candidate.value}"
    return f"{candidate.label}은 자료에서 확인되었습니다."


def _needs_review_body(
    *, candidate: AnswerCandidate, certification: Certification
) -> str:
    # governed_by_condition: 값은 자료에 있으나 그 값을 지배하는 조건이 함께 있어
    # 확정으로 볼 수 없다. 조건 원문을 그대로 길게 노출하지 않고, 조건이 걸려 있어
    # 확인이 필요하다는 사실만 전한다(state를 거슬러 "확정"으로 말하지 않는다, AC5).
    if certification.reason == "governed_by_condition":
        if candidate.value:
            return (
                f"{candidate.label}은 자료에서 확인되지만, 적용에 조건이 있어 "
                f"확정 여부는 원문 확인이 필요합니다: {candidate.value}"
            )
        return f"{candidate.label}은 적용 조건이 있어 원문 확인이 필요합니다."
    if candidate.value:
        return (
            f"{candidate.label}은 자료에서 확인되지만 보장 여부는 "
            f"원문 확인이 필요합니다: {candidate.value}"
        )
    return f"{candidate.label}은 원문 확인이 필요합니다."


def _missing_body(*, candidate: AnswerCandidate, certification: Certification) -> str:
    if certification.reason == "candidate_missing":
        return f"현재 등록된 자료에서 {candidate.label}을 확인하지 못했습니다."
    return f"현재 등록된 자료에서 {candidate.label}의 근거를 확인하지 못했습니다."


def _summary_for_items(items: list[ChatAnswerItem]) -> str:
    supported_count = sum(
        item.evidence_state == EvidenceState.SUPPORTED for item in items
    )
    needs_review_count = sum(
        item.evidence_state == EvidenceState.NEEDS_REVIEW for item in items
    )
    missing_count = sum(item.evidence_state == EvidenceState.MISSING for item in items)
    if supported_count and (needs_review_count or missing_count):
        return "자료에서 확인한 내용과 추가 확인이 필요한 항목입니다."
    if supported_count:
        return "자료에서 확인한 답변입니다."
    if needs_review_count:
        return "자료에 있으나 확정 여부는 원문 확인이 필요한 항목입니다."
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
