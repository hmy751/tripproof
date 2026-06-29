from __future__ import annotations

from dataclasses import dataclass

from server.answers.library_chat_payload import (
    NormalizedAnswerItemPayload,
    normalize_answer_item_payload,
)
from server.extraction.models import EvidenceState, GoverningCondition


@dataclass(frozen=True)
class AnswerCandidate:
    """LLM이 만든 답변 후보.

    후보는 최종 `evidence_state`도, 사용자-facing 최종 body도 소유하지 않는다.
    `proposed_state`와 `draft_body`는 코드 certification의 advisory 입력일 뿐
    제품 상태/문장이 아니며, 코드가 그대로 `ChatAnswerItem`으로 projection하지
    않는다(04 단계 계약: LLM 후보 -> code certification -> final body).

    `governing_condition`은 의미 층(06)이 낸 '이 값을 지배하는 조건' 역할이다. 코드는
    이 역할을 만들지 않고 받아서, 그 snippet이 원문에 grounding되는지(구조)만 보고
    상태를 내린다. 없으면 None.
    """

    index: int
    label: str
    value: str | None
    draft_body: str
    proposed_state: EvidenceState
    cited_source_unit_id: str | None
    evidence_snippet: str | None
    governing_condition: GoverningCondition | None
    normalized: NormalizedAnswerItemPayload

    def item_id(self) -> str:
        return self.normalized.item_id(index=self.index)


def answer_candidate_from_payload(
    *,
    index: int,
    question: str,
    payload: object,
) -> AnswerCandidate | None:
    """LLM payload 한 건을 후보로 정규화한다.

    `question`은 label/draft 문장을 다듬는 display 용도로만 쓰인다. certification은
    이 후보와 retrieval 구조만 보고 final state를 정하며 질문 문구를 보지 않는다.
    """

    normalized = normalize_answer_item_payload(question=question, payload=payload)
    if normalized is None:
        return None
    return AnswerCandidate(
        index=index,
        label=normalized.label,
        value=normalized.value,
        draft_body=normalized.body,
        proposed_state=normalized.evidence_state,
        cited_source_unit_id=normalized.source_unit_id,
        evidence_snippet=normalized.evidence_snippet,
        governing_condition=normalized.governing_condition,
        normalized=normalized,
    )
