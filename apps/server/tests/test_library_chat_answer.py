from __future__ import annotations

import re
from pathlib import Path

from server.answers.library_chat import LIBRARY_CHAT_TARGET_ID, OllamaLibraryChatAnswerComposer
from server.answers.prompts.loaders.library_chat_answer_prompt import load_library_chat_prompt
from server.extraction.models import EvidenceState
from server.retrieval.models import ContextPack, RetrievalCandidate, SourceUnit


FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "accommodation-checkin"


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


def test_library_chat_composer_uses_versioned_prompt_asset() -> None:
    unit = _source_unit("Check-in starts at 15:00.")
    client = _CapturingJsonClient(
        {
            "items": [
                {
                    "id": "answer",
                    "label": "체크인 시작 시각",
                    "body": "체크인 시작 시각은 15:00입니다.",
                    "value": "15:00",
                    "evidence_state": "supported",
                    "source_unit_id": unit.id,
                    "evidence_snippet": "Check-in starts at 15:00.",
                }
            ]
        }
    )
    composer = OllamaLibraryChatAnswerComposer(client=client)

    composer.compose(question="체크인 시작 시각은 몇 시야?", context=_context(unit))

    prompt = load_library_chat_prompt()
    assert composer.prompt_asset.category == "llm"
    assert composer.prompt_asset.name == "library_chat_answer"
    assert composer.prompt_asset.version == "2026-06-10"
    assert composer.prompt_asset.metadata["display_name_ko"] == "자료함 질문 답변"
    assert composer.prompt_asset.metadata["description_ko"] == (
        "자료함 질문에 대해 제공된 source unit 근거만 사용해 답변 후보를 만든다."
    )
    assert composer.prompt_asset.snapshot()["contentHash"] == prompt.content_hash
    assert composer.prompt_asset.snapshot()["assetPath"] == (
        "apps/server/answers/prompts/llm/library_chat_answer/2026-06-10.md"
    )
    assert "displayNameKo" not in composer.prompt_asset.snapshot()
    assert "descriptionKo" not in composer.prompt_asset.snapshot()
    assert client.last_system == prompt.section("System")
    assert client.last_user is not None
    assert "question: 체크인 시작 시각은 몇 시야?" in client.last_user
    assert "source_unit_id: su_mat_1_1" in client.last_user
    assert "Check-in starts at 15:00." in client.last_user
    assert "자료함 질문 답변" not in client.last_system
    assert "자료함 질문 답변" not in client.last_user
    assert "일반 여행 지식으로 추론하지 않는다." not in client.last_system
    assert "일반 여행 지식으로 추론하지 않는다." not in client.last_user


def test_library_chat_answer_changes_when_only_source_checkin_time_changes() -> None:
    question = "체크인 시작 시각은 몇 시야?"
    base_unit = _source_unit(
        "Agoda Fukuoka booking confirmation\n"
        "Hotel address is Hakata.\n"
        "Check-in starts at 15:00.\n"
        "Check-out is at 11:00."
    )
    variant_unit = _source_unit((FIXTURE_ROOT / "agoda-fukuoka-checkin-start-1600.txt").read_text())
    composer = OllamaLibraryChatAnswerComposer(client=_SourceDrivenCheckinTimeJsonClient())

    base_answer = composer.compose(question=question, context=_context(base_unit, query=question))
    variant_answer = composer.compose(question=question, context=_context(variant_unit, query=question))

    base_item = base_answer.items[0]
    variant_item = variant_answer.items[0]
    assert base_item.evidence_state == EvidenceState.SUPPORTED
    assert variant_item.evidence_state == EvidenceState.SUPPORTED
    assert "15:00" in f"{base_item.value} {base_item.body}"
    assert "16:00" not in f"{base_item.value} {base_item.body}"
    assert "16:00" in f"{variant_item.value} {variant_item.body}"
    assert "15:00" not in f"{variant_item.value} {variant_item.body}"
    assert base_item.evidence[0].snippet in base_unit.text
    assert variant_item.evidence[0].snippet in variant_unit.text


def test_library_chat_supported_items_return_evidence_snippets_from_source_text() -> None:
    unit = _source_unit("체크인 시\n예약 확정서를\n제시해 주세요.\nCheck-in starts at 15:00.")
    composer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(
            {
                "items": [
                    {
                        "id": "booking_confirmation",
                        "label": "체크인 제시물",
                        "body": "체크인 시 예약 확정서를 제시하면 됩니다.",
                        "value": "예약 확정서",
                        "evidence_state": "supported",
                        "source_unit_id": unit.id,
                        "evidence_snippet": "체크인 시 예약 확정서를 제시해 주세요.",
                    },
                    {
                        "id": "checkin_start_time",
                        "label": "체크인 시작 시각",
                        "body": "체크인 시작 시각은 15:00입니다.",
                        "value": "15:00",
                        "evidence_state": "supported",
                        "source_unit_id": unit.id,
                        "evidence_snippet": "Check-in starts at 15:00.",
                    },
                ]
            }
        )
    )

    answer = composer.compose(question="체크인 자료에서 확인되는 항목은 뭐야?", context=_context(unit))

    assert len(answer.items) == 2
    for item in answer.items:
        assert item.evidence_state == EvidenceState.SUPPORTED
        assert item.evidence
        for evidence in item.evidence:
            assert evidence.snippet in unit.text


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


def _context(unit: SourceUnit, *, query: str = "체크인 날짜가 어떻게 돼?") -> ContextPack:
    return ContextPack(
        target_id=LIBRARY_CHAT_TARGET_ID,
        query=query,
        candidates=[
            RetrievalCandidate(
                target_id=LIBRARY_CHAT_TARGET_ID,
                query=query,
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


class _CapturingJsonClient(_FakeJsonClient):
    def __init__(self, payload: object) -> None:
        super().__init__(payload)
        self.last_system = None
        self.last_user = None

    def generate_json(self, *, system: str, user: str) -> object:
        self.last_system = system
        self.last_user = user
        return super().generate_json(system=system, user=user)


class _SourceDrivenCheckinTimeJsonClient:
    def generate_json(self, *, system: str, user: str) -> object:
        source_unit_id_match = re.search(r"source_unit_id: (?P<source_unit_id>\S+)", user)
        time_match = re.search(r"Check-in starts at (?P<time>\d{2}:\d{2})\.", user)
        if source_unit_id_match is None or time_match is None:
            return {
                "items": [
                    {
                        "id": "checkin_start_time",
                        "label": "체크인 시작 시각",
                        "body": "현재 등록된 자료에서 체크인 시작 시각을 확인하지 못했습니다.",
                        "value": None,
                        "evidence_state": "missing",
                        "source_unit_id": None,
                        "evidence_snippet": None,
                    }
                ]
            }

        time = time_match.group("time")
        return {
            "items": [
                {
                    "id": "checkin_start_time",
                    "label": "체크인 시작 시각",
                    "body": f"체크인 시작 시각은 {time}입니다.",
                    "value": time,
                    "evidence_state": "supported",
                    "source_unit_id": source_unit_id_match.group("source_unit_id"),
                    "evidence_snippet": f"Check-in starts at {time}.",
                }
            ]
        }
