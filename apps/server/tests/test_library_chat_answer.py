from __future__ import annotations

from server.answers.library_chat import LIBRARY_CHAT_TARGET_ID, OllamaLibraryChatAnswerComposer
from server.extraction.models import EvidenceState
from server.retrieval.models import ContextPack, RetrievalCandidate, SourceUnit


def test_library_chat_composer_answers_question_from_grounded_source() -> None:
    unit = _source_unit("Arrival :\n체크인 :\n2025년 3월 09일\nDeparture :\n체크아웃 :\n2025년 3월 13일")
    composer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(
            {
                "items": [
                    {
                        "id": "answer",
                        "label": "체크인 날짜",
                        "body": "체크인 날짜는 2025년 3월 09일입니다.",
                        "value": "2025년 3월 09일",
                        "evidence_state": "supported",
                        "source_unit_id": unit.id,
                        "evidence_snippet": "Arrival : 체크인 : 2025년 3월 09일",
                    }
                ]
            }
        )
    )

    answer = composer.compose(question="체크인 날짜가 어떻게 돼?", context=_context(unit))

    assert answer.summary == "자료에서 확인한 답변입니다."
    assert len(answer.items) == 1
    item = answer.items[0]
    assert item.id == "answer"
    assert item.label == "체크인 날짜"
    assert item.body == "체크인 날짜는 2025년 3월 09일입니다."
    assert item.evidence_state == EvidenceState.SUPPORTED
    assert item.evidence[0].snippet in unit.text
    assert item.evidence[0].locator == "booking.pdf p.1 u.1"


def test_library_chat_composer_downgrades_ungrounded_supported_answer() -> None:
    unit = _source_unit("체크인 날짜는 2025년 3월 09일입니다.")
    composer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(
            {
                "items": [
                    {
                        "id": "answer",
                        "label": "체크인 날짜",
                        "body": "체크인 날짜는 2025년 3월 10일입니다.",
                        "value": "2025년 3월 10일",
                        "evidence_state": "supported",
                        "source_unit_id": unit.id,
                        "evidence_snippet": "체크인 날짜는 2025년 3월 10일입니다.",
                    }
                ]
            }
        )
    )

    answer = composer.compose(question="체크인 날짜가 어떻게 돼?", context=_context(unit))

    assert answer.summary == "현재 등록된 자료만으로는 답을 확인하지 못했습니다."
    assert answer.items[0].evidence_state == EvidenceState.MISSING
    assert answer.items[0].value is None
    assert answer.items[0].evidence == []


def test_library_chat_composer_downgrades_date_answer_when_question_asks_time() -> None:
    unit = _source_unit("Arrival : 체크인 : 2025년 3월 09일")
    composer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(
            {
                "items": [
                    {
                        "id": "answer",
                        "label": "체크인 시작 시각",
                        "body": "체크인 시작 시각은 2025년 3월 09일입니다.",
                        "value": "2025년 3월 09일",
                        "evidence_state": "supported",
                        "source_unit_id": unit.id,
                        "evidence_snippet": "Arrival : 체크인 : 2025년 3월 09일",
                    }
                ]
            }
        )
    )

    answer = composer.compose(question="체크인 시작 시각은 몇 시야?", context=_context(unit))

    assert answer.summary == "현재 등록된 자료만으로는 답을 확인하지 못했습니다."
    assert answer.items[0].evidence_state == EvidenceState.MISSING
    assert answer.items[0].value is None
    assert answer.items[0].evidence == []


def test_library_chat_composer_repairs_numeric_value_snippet_from_pdf_extracted_text() -> None:
    unit = _source_unit(
        "Arrival :\n"
        "체크인\n"
        "체크인\n"
        ":\n"
        "2025\n"
        "년\n"
        "년\n"
        "3\n"
        "월\n"
        "월\n"
        "09\n"
        "일\n"
        "일\n"
        "Departure :\n"
        "체크아웃 : 2025년 3월 13일"
    )
    composer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(
            {
                "items": [
                    {
                        "id": "su_mat_1_1",
                        "label": "2025년 3월 9일",
                        "body": "2025년 3월 9일",
                        "value": "2025년 3월 9일",
                        "evidence_state": "supported",
                        "source_unit_id": unit.id,
                        "evidence_snippet": "2025년 3월 9일",
                    }
                ]
            }
        )
    )

    answer = composer.compose(question="체크인 날짜가 어떻게 돼?", context=_context(unit))

    item = answer.items[0]
    assert item.id == "answer_1"
    assert item.label == "답변"
    assert item.body == "체크인 날짜: 2025년 3월 9일"
    assert item.evidence_state == EvidenceState.SUPPORTED
    assert "체크인" in item.evidence[0].snippet
    assert "09" in item.evidence[0].snippet
    assert "2025년 3월 13일" not in item.evidence[0].snippet
    assert "Departure" not in item.evidence[0].snippet


def _source_unit(text: str) -> SourceUnit:
    return SourceUnit(
        id="su_mat_1_1",
        material_id="mat_1",
        file_name="booking.pdf",
        page=1,
        unit_index=1,
        locator="booking.pdf p.1 u.1",
        text=text,
        search_text=" ".join(text.split()),
        start=0,
        end=len(text),
    )


def _context(unit: SourceUnit) -> ContextPack:
    return ContextPack(
        target_id=LIBRARY_CHAT_TARGET_ID,
        query="체크인 날짜가 어떻게 돼?",
        candidates=[
            RetrievalCandidate(
                target_id=LIBRARY_CHAT_TARGET_ID,
                query="체크인 날짜가 어떻게 돼?",
                source_unit=unit,
                score=1.0,
                lexical_score=1,
                vector_score=None,
            )
        ],
    )


class _FakeJsonClient:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def generate_json(self, *, system: str, user: str) -> object:
        return self._payload
