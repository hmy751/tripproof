from __future__ import annotations

import inspect
from dataclasses import fields

from server.answers.candidate import AnswerCandidate, answer_candidate_from_payload
from server.answers.certification import certify
from server.answers.library_chat import (
    LIBRARY_CHAT_TARGET_ID,
    OllamaLibraryChatAnswerComposer,
)
from server.extraction.models import EvidenceState
from server.questions.observation import answer_item_detail
from server.retrieval.models import AnswerContext, RetrievedSource, SourceUnit

# 04 사용자 장면: 특별 요청 값과 그것을 조건부로 만드는 caveat가 같은 자료에 함께
# 있다. 실제 원문(fixtures/accommodation-checkin/agoda-booking-confirmation-sample.txt)의
# Remarks 영역을 구조 단위로 재현한다.
_VALUE_UNIT = "NonSmoke, LargeBed"
_CONDITION_UNIT = "All special requests are subject to availability at check-in."


def _unit(
    *, unit_id: str, text: str, kind: str = "general", page: int = 1
) -> SourceUnit:
    return SourceUnit(
        id=unit_id,
        material_id="mat_1",
        file_name="booking.pdf",
        page=page,
        unit_index=1,
        locator=f"booking.pdf p.{page} u.1",
        text=text,
        search_text=" ".join(text.split()),
        start=0,
        end=len(text),
        metadata={"kind": kind, "page": page},
    )


def _context(*units: SourceUnit, query: str = "특별 요청") -> AnswerContext:
    return AnswerContext(
        target_id=LIBRARY_CHAT_TARGET_ID,
        query=query,
        candidates=[
            RetrievedSource(
                target_id=LIBRARY_CHAT_TARGET_ID,
                query=query,
                source_unit=unit,
                score=1.0,
                lexical_score=1,
                vector_score=None,
            )
            for unit in units
        ],
    )


def _special_request_payload(*, value: str, source_unit_id: str) -> dict:
    return {
        "items": [
            {
                "id": "special_request",
                "label": "특별 요청",
                "body": "NonSmoke와 LargeBed는 확정된 조건입니다.",
                "value": value,
                "evidence_state": "supported",
                "source_unit_id": source_unit_id,
                "evidence_snippet": _VALUE_UNIT,
            }
        ]
    }


def _caveat_payload(
    *,
    value: str,
    value_source_id: str,
    condition_source_id: str,
    condition_snippet: str,
) -> dict:
    # 06 의미 층이 낸 caveat 역할이 함께 들어온 후보. 값은 grounding되지만
    # 그 값을 지배하는 조건이 함께 있다.
    return {
        "items": [
            {
                "id": "special_request",
                "label": "특별 요청",
                "body": "NonSmoke와 LargeBed는 확정된 조건입니다.",
                "value": value,
                "evidence_state": "supported",
                "source_unit_id": value_source_id,
                "evidence_snippet": _VALUE_UNIT,
                "caveat": {
                    "source_unit_id": condition_source_id,
                    "snippet": condition_snippet,
                    "text": _CONDITION_UNIT,
                },
            }
        ]
    }


# ── AC1: candidate 타입에는 final body/state가 없다 ──────────────────────────
def test_answer_candidate_has_no_final_body_or_state() -> None:
    field_names = {field.name for field in fields(AnswerCandidate)}
    # 최종 product 필드(final body, final evidence_state)는 candidate에 없다.
    assert "evidence_state" not in field_names
    assert "body" not in field_names
    # 있는 것은 advisory 신호뿐이다.
    assert "proposed_state" in field_names
    assert "draft_body" in field_names


# ── AC2: certification은 question/body free text를 입력으로 받지 않는다 ───────
def test_certify_signature_excludes_question_and_body_text() -> None:
    params = set(inspect.signature(certify).parameters)
    assert params == {"candidate", "context"}
    assert "question" not in params
    assert "body" not in params


# ── AC3: value-only evidence만으로 "확정"을 supported로 만들지 않는다 ─────────
def test_value_only_special_request_is_not_supported() -> None:
    # 실제 P1-01 실패는 value="확정"으로 들어왔다. "확정"은 근거에 실재하지 않으므로
    # value-grounding이 구조적으로 막는다(단어를 읽어 막는 게 아니다).
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    candidate = answer_candidate_from_payload(
        index=1,
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        payload=_special_request_payload(value="확정", source_unit_id=value_unit.id)[
            "items"
        ][0],
    )
    assert candidate is not None

    certification = certify(candidate=candidate, context=_context(value_unit))

    assert certification.state != EvidenceState.SUPPORTED
    assert certification.state == EvidenceState.NEEDS_REVIEW
    assert certification.reason == "value_not_grounded"


# ── 경계: 같은 page의 조건 unit으로는 코드가 더 이상 강등하지 않는다 ──────────
def test_colocated_condition_is_not_downgraded_by_code() -> None:
    # 구현 범위 재조정(2026-06-29): "조건이 이 값에 걸리나"는 코드가 kind/page 근접으로
    # 추정하지 않는다(실제 문서에서 무관한 값까지 강등시켜서). 값이 실제 grounding되면,
    # 같은 page에 조건 kind unit이 있어도 코드는 supported로 둔다. 조건-지배 판단은
    # 의미 층(relation/entailment, 05 위)으로 재귀속됐다.
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    condition_unit = _unit(
        unit_id="su_condition", text=_CONDITION_UNIT, kind="request_note"
    )
    candidate = answer_candidate_from_payload(
        index=1,
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        payload=_special_request_payload(
            value=_VALUE_UNIT, source_unit_id=value_unit.id
        )["items"][0],
    )
    assert candidate is not None

    certification = certify(
        candidate=candidate, context=_context(value_unit, condition_unit)
    )

    assert certification.state == EvidenceState.SUPPORTED
    assert certification.reason == "grounded_value"


# ── paraphrase 회귀: 같은 후보/근거면 질문 표현이 달라도 같은 state ───────────
def test_certification_is_paraphrase_invariant() -> None:
    # certify는 질문을 보지 않으므로 표현이 달라도 결과가 같다. 여기서는 실제 P1-01
    # 실패 형태(value="확정")로, value-grounding이 두 표현 모두에서 동일하게 강등시킨다.
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    payload = _special_request_payload(value="확정", source_unit_id=value_unit.id)

    keyworded = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(payload)
    ).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit),
    )
    paraphrased = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(payload)
    ).compose(
        # 같은 의미, "확정/조건" 키워드 없음.
        question="금연이랑 큰 침대는 그냥 되는 거지?",
        context=_context(value_unit),
    )

    assert keyworded.items[0].evidence_state == EvidenceState.NEEDS_REVIEW
    assert paraphrased.items[0].evidence_state == EvidenceState.NEEDS_REVIEW
    assert keyworded.items[0].evidence_state == paraphrased.items[0].evidence_state


# ── AC5: final body는 certified state를 거슬러 "확정"처럼 말할 수 없다 ─────────
def test_needs_review_body_does_not_assert_confirmation() -> None:
    # LLM이 needs_review를 제안하면서도 draft body에 "확정된 조건입니다"를 썼더라도,
    # needs_review final body는 코드 template으로 만들어 그 overclaim이 새지 않는다.
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    payload = {
        "items": [
            {
                "id": "special_request",
                "label": "특별 요청",
                "body": "NonSmoke와 LargeBed는 확정된 조건입니다.",
                "value": _VALUE_UNIT,
                "evidence_state": "needs_review",
                "source_unit_id": value_unit.id,
                "evidence_snippet": _VALUE_UNIT,
            }
        ]
    }

    answer = OllamaLibraryChatAnswerComposer(client=_FakeJsonClient(payload)).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit),
    )

    item = answer.items[0]
    assert item.evidence_state == EvidenceState.NEEDS_REVIEW
    # LLM draft body의 "확정된 조건입니다"가 final body로 새지 않는다.
    assert "확정된 조건입니다" not in item.body
    assert answer.summary != "자료에서 확인한 답변입니다."


# ── 경계: 조건 kind source를 인용했다는 이유만으로는 코드가 강등하지 않는다 ────
def test_policy_kind_source_is_not_downgraded_by_code() -> None:
    # 구현 범위 재조정 이후: conditional_source_kind 강등은 제거됐다(정책이 답인
    # 질문에서 정책 문단 인용은 정상인데, "정책 kind를 인용했다"만으로 강등하면
    # 정당한 답까지 needs_review가 됐다). 정책이 질문에 충분히 답하는지(부분 vs 전체)는
    # 의미 판단이라 의미 층의 몫이다. 코드는 grounding/value-grounding만 본다.
    policy_unit = _unit(
        unit_id="su_policy",
        text="No-show results in a charge of the first night.",
        kind="policy",
    )
    candidate = answer_candidate_from_payload(
        index=1,
        question="노쇼하면 어떻게 돼?",
        payload={
            "id": "noshow",
            "label": "노쇼 정책",
            "body": "노쇼 시 첫 박 요금이 청구됩니다.",
            "value": "first night",
            "evidence_state": "supported",
            "source_unit_id": policy_unit.id,
            "evidence_snippet": "charge of the first night",
        },
    )
    assert candidate is not None

    certification = certify(candidate=candidate, context=_context(policy_unit))

    assert certification.state == EvidenceState.SUPPORTED
    assert certification.reason == "grounded_value"


# ── 경계: 조건 없는 순수 값 lookup은 여전히 supported (over-downgrade 방지) ────
def test_plain_value_lookup_without_condition_stays_supported() -> None:
    value_unit = _unit(
        unit_id="su_value",
        text="Remarks: NonSmoke, LargeBed",
        kind="label_value",
    )
    candidate = answer_candidate_from_payload(
        index=1,
        question="특별 요청에 뭐가 있어?",
        payload={
            "id": "special_request",
            "label": "특별 요청",
            "body": "특별 요청에는 NonSmoke, LargeBed가 있습니다.",
            "value": _VALUE_UNIT,
            "evidence_state": "supported",
            "source_unit_id": value_unit.id,
            "evidence_snippet": _VALUE_UNIT,
        },
    )
    assert candidate is not None

    certification = certify(candidate=candidate, context=_context(value_unit))

    assert certification.state == EvidenceState.SUPPORTED
    assert certification.reason == "grounded_value"


# ── certification은 LLM 후보를 끌어올리지 않고 ceiling으로 둔다 ───────────────
def test_certification_does_not_upgrade_candidate() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    candidate = answer_candidate_from_payload(
        index=1,
        question="특별 요청에 뭐가 있어?",
        payload={
            "id": "special_request",
            "label": "특별 요청",
            "body": "확인이 필요합니다.",
            "value": _VALUE_UNIT,
            "evidence_state": "needs_review",
            "source_unit_id": value_unit.id,
            "evidence_snippet": _VALUE_UNIT,
        },
    )
    assert candidate is not None

    certification = certify(candidate=candidate, context=_context(value_unit))

    # 후보가 needs_review를 제안했으면 구조가 supportable해도 끌어올리지 않는다.
    assert certification.state == EvidenceState.NEEDS_REVIEW
    assert certification.proposed_state == EvidenceState.NEEDS_REVIEW


# ── AC7: candidate -> certification 전이가 관측 record에 남는다 ───────────────
def test_certification_transition_is_observable() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    payload = _special_request_payload(value="확정", source_unit_id=value_unit.id)

    answer = OllamaLibraryChatAnswerComposer(client=_FakeJsonClient(payload)).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit),
    )

    detail = answer_item_detail(answer.items[0])
    certification = detail["certification"]
    assert certification is not None
    # LLM은 supported를 제안했지만 코드 certification은 needs_review로 내렸고,
    # 그 전이와 근거가 report에서 before/after로 보인다.
    assert certification["proposed_state"] == "supported"
    assert certification["state"] == "needs_review"
    assert certification["reason"] == "value_not_grounded"


# ── 06: 의미 층이 붙인 caveat이 grounding되면 grounded 값도 강등 ─────
def test_caveat_downgrades_grounded_value() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    condition_unit = _unit(
        unit_id="su_condition", text=_CONDITION_UNIT, kind="request_note"
    )
    candidate = answer_candidate_from_payload(
        index=1,
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        payload=_caveat_payload(
            value=_VALUE_UNIT,
            value_source_id=value_unit.id,
            condition_source_id=condition_unit.id,
            condition_snippet="subject to availability",
        )["items"][0],
    )
    assert candidate is not None

    certification = certify(
        candidate=candidate, context=_context(value_unit, condition_unit)
    )

    # 값은 grounding됐지만(value_not_grounded 아님) 의미 층이 붙인 caveat이
    # 원문에 grounding되므로 단독 supported가 아니라 needs_review로 내린다.
    assert certification.state == EvidenceState.NEEDS_REVIEW
    assert certification.reason == "limited_by_caveat"
    assert certification.caveat is not None


# ── 06 경계: grounding 안 되는 조건 주장(hallucination 가능)에는 강등하지 않는다 ──
def test_ungrounded_caveat_does_not_downgrade() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    # 조건 unit을 context에 넣지 않는다 → LLM이 낸 조건 snippet이 원문에 grounding 안 됨.
    candidate = answer_candidate_from_payload(
        index=1,
        question="특별 요청에 뭐가 있어?",
        payload=_caveat_payload(
            value=_VALUE_UNIT,
            value_source_id=value_unit.id,
            condition_source_id="su_condition_absent",
            condition_snippet="subject to availability",
        )["items"][0],
    )
    assert candidate is not None

    certification = certify(candidate=candidate, context=_context(value_unit))

    # 코드는 검증되지 않은(grounding 안 된) 조건 주장으로 강등하지 않는다.
    assert certification.state == EvidenceState.SUPPORTED
    assert certification.reason == "grounded_value"


# ── 06 binding paraphrase: caveat이 있으면 질문 표현과 무관하게 강등 ──
def test_caveat_is_paraphrase_invariant() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    condition_unit = _unit(
        unit_id="su_condition", text=_CONDITION_UNIT, kind="request_note"
    )
    payload = _caveat_payload(
        value=_VALUE_UNIT,
        value_source_id=value_unit.id,
        condition_source_id=condition_unit.id,
        condition_snippet="subject to availability",
    )

    keyworded = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(payload)
    ).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit, condition_unit),
    )
    paraphrased = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(payload)
    ).compose(
        # 같은 의미, "확정/조건" 키워드 없음.
        question="금연이랑 큰 침대는 그냥 되는 거지?",
        context=_context(value_unit, condition_unit),
    )

    # certify는 질문을 안 보고 caveat 역할 구조만 읽으므로, 같은 후보면
    # 표현이 달라도 둘 다 needs_review(limited_by_caveat)다.
    assert keyworded.items[0].evidence_state == EvidenceState.NEEDS_REVIEW
    assert paraphrased.items[0].evidence_state == EvidenceState.NEEDS_REVIEW
    assert keyworded.items[0].certification is not None
    assert paraphrased.items[0].certification is not None
    assert keyworded.items[0].certification.reason == "limited_by_caveat"
    assert paraphrased.items[0].certification.reason == "limited_by_caveat"


# ── 06: limited_by_caveat body는 조건을 전하되 "확정"으로 말하지 않는다 ──────
def test_limited_by_caveat_body_does_not_assert_confirmation() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    condition_unit = _unit(
        unit_id="su_condition", text=_CONDITION_UNIT, kind="request_note"
    )
    payload = _caveat_payload(
        value=_VALUE_UNIT,
        value_source_id=value_unit.id,
        condition_source_id=condition_unit.id,
        condition_snippet="subject to availability",
    )

    answer = OllamaLibraryChatAnswerComposer(client=_FakeJsonClient(payload)).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit, condition_unit),
    )

    item = answer.items[0]
    assert item.evidence_state == EvidenceState.NEEDS_REVIEW
    # LLM draft body의 "확정된 조건입니다"가 final body로 새지 않는다.
    assert "확정된 조건입니다" not in item.body
    # 조건이 걸려 확인이 필요하다는 사실은 전한다.
    assert "조건" in item.body


# ── 06: caveat 관측이 report에 남는다 (응답 body 아님) ───────────
def test_caveat_is_observable() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE_UNIT, kind="label_value")
    condition_unit = _unit(
        unit_id="su_condition", text=_CONDITION_UNIT, kind="request_note"
    )
    payload = _caveat_payload(
        value=_VALUE_UNIT,
        value_source_id=value_unit.id,
        condition_source_id=condition_unit.id,
        condition_snippet="subject to availability",
    )

    answer = OllamaLibraryChatAnswerComposer(client=_FakeJsonClient(payload)).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit, condition_unit),
    )

    detail = answer_item_detail(answer.items[0])
    certification = detail["certification"]
    assert certification is not None
    assert certification["state"] == "needs_review"
    assert certification["reason"] == "limited_by_caveat"
    assert certification["caveat_snippet"] == "subject to availability"


class _FakeJsonClient:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def generate_json(self, *, system: str, user: str) -> object:
        return self._payload
