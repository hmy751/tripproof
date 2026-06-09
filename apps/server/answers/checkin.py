from __future__ import annotations

from collections.abc import Iterable

from server.extraction.checkin import BOOKING_CONFIRMATION_FACT_ID, CHECKIN_START_TIME_FACT_ID
from server.extraction.models import EvidenceState, FactCandidate
from server.schemas.answers import ChatAnswerItemResponse, ChatAnswerResponse


def build_checkin_chat_answer(*, facts: Iterable[FactCandidate]) -> ChatAnswerResponse:
    answer_items = [_answer_item_from_fact(fact) for fact in _ordered_checkin_facts(facts)]

    if not answer_items:
        return ChatAnswerResponse(summary="현재 자료에서 답변할 체크인 항목을 찾지 못했습니다.")

    supported_count = sum(item.evidence_state == EvidenceState.SUPPORTED for item in answer_items)
    missing_count = sum(item.evidence_state == EvidenceState.MISSING for item in answer_items)
    if supported_count and missing_count:
        summary = "현재 자료에서 확인한 내용과 확인되지 않은 항목입니다."
    elif supported_count:
        summary = "현재 자료에서 확인한 내용입니다."
    else:
        summary = "현재 등록된 자료만으로는 요청한 항목을 확인하지 못했습니다."

    return ChatAnswerResponse(summary=summary, items=answer_items)


def _ordered_checkin_facts(facts: Iterable[FactCandidate]) -> list[FactCandidate]:
    facts_by_id = {fact.id: fact for fact in facts}
    ordered_ids = (BOOKING_CONFIRMATION_FACT_ID, CHECKIN_START_TIME_FACT_ID)
    ordered = [facts_by_id[fact_id] for fact_id in ordered_ids if fact_id in facts_by_id]
    extras = [fact for fact in facts if fact.id not in ordered_ids]
    return [*ordered, *extras]


def _answer_item_from_fact(fact: FactCandidate) -> ChatAnswerItemResponse:
    return ChatAnswerItemResponse.from_fact(fact=fact, body=_body_for_fact(fact))


def _body_for_fact(fact: FactCandidate) -> str:
    if fact.evidence_state == EvidenceState.SUPPORTED:
        return _supported_body_for_fact(fact)
    if fact.evidence_state == EvidenceState.MISSING:
        return _missing_body_for_fact(fact)
    if fact.evidence_state == EvidenceState.CONFLICT:
        return f"{fact.label}은 현재 자료 사이에 서로 다른 내용이 있어 확정할 수 없습니다."
    return f"{fact.label}은 원문 확인이 필요합니다."


def _supported_body_for_fact(fact: FactCandidate) -> str:
    if fact.id == BOOKING_CONFIRMATION_FACT_ID:
        value = _booking_confirmation_display_value(fact.value)
        return f"체크인 시 제시할 자료는 {value}입니다."
    if fact.id == CHECKIN_START_TIME_FACT_ID:
        return f"체크인 시작 시각은 {fact.value}입니다."
    if fact.value:
        return f"{fact.label}: {fact.value}"
    return f"{fact.label}은 현재 자료에서 근거를 확인했습니다."


def _missing_body_for_fact(fact: FactCandidate) -> str:
    if fact.id == CHECKIN_START_TIME_FACT_ID:
        return "현재 등록된 자료에서 체크인 시작 시각을 확인하지 못했습니다."
    return f"현재 등록된 자료에서 {fact.label}을 확인하지 못했습니다."


def _booking_confirmation_display_value(value: str | None) -> str:
    normalized_value = " ".join((value or "").split())
    if "전자" in normalized_value and "인쇄" in normalized_value:
        return "예약 확정서의 전자 사본 또는 인쇄본"
    if "예약 확정서" in normalized_value:
        return "예약 확정서"
    if "booking confirmation" in normalized_value.lower():
        return "booking confirmation"
    return normalized_value or "예약 확정서"
