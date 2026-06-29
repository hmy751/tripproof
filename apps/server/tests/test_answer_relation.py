from __future__ import annotations

from server.answers.candidate import answer_candidate_from_payload
from server.answers.library_chat import (
    LIBRARY_CHAT_TARGET_ID,
    OllamaLibraryChatAnswerComposer,
)
from server.answers.relation import OllamaCaveatExtractor
from server.extraction.models import EvidenceState, Caveat
from server.retrieval.models import AnswerContext, RetrievedSource, SourceUnit

# 06 robust fix: 답변 생성과 분리된 두 번째 호출이 '값을 좌우하는 조건'을 채운다.
# 실제 run 16의 P1-01 형태를 재현한다 — 답변 호출이 조건을 답(body)으로 흡수하고
# value=null, supported, caveat 없이 내놓는 경우.
_VALUE = "NonSmoke, LargeBed"
_CONDITION = "All special requests are subject to availability at check-in."


def _unit(*, unit_id: str, text: str) -> SourceUnit:
    return SourceUnit(
        id=unit_id,
        material_id="mat_1",
        file_name="booking.pdf",
        page=1,
        unit_index=1,
        locator=f"booking.pdf p.1 u.1 ({unit_id})",
        text=text,
        search_text=" ".join(text.split()),
        start=0,
        end=len(text),
        metadata={"kind": "request_note", "page": 1},
    )


def _context(*units: SourceUnit) -> AnswerContext:
    return AnswerContext(
        target_id=LIBRARY_CHAT_TARGET_ID,
        query="특별 요청",
        candidates=[
            RetrievedSource(
                target_id=LIBRARY_CHAT_TARGET_ID,
                query="특별 요청",
                source_unit=unit,
                score=1.0,
                lexical_score=1,
                vector_score=None,
            )
            for unit in units
        ],
    )


class _FakeJsonClient:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def generate_json(self, *, system: str, user: str) -> object:
        return self._payload


class _FakeExtractor:
    """주입형 relation extractor — 항상 같은 조건을 돌려준다."""

    def __init__(self, caveat: Caveat | None) -> None:
        self._caveat = caveat
        self.called = False

    def extract(self, *, question, candidate, context) -> Caveat | None:
        self.called = True
        return self._caveat


class _ExplodingExtractor:
    """호출되면 실패하는 extractor — '호출되지 않아야 한다'를 검증할 때 쓴다."""

    def extract(self, *, question, candidate, context) -> Caveat | None:
        raise AssertionError("relation extractor should not be called")


def _p1_01_style_payload() -> dict:
    # run 16 P1-01 실제 형태: 조건을 답으로 흡수, value=null, supported, 조건칸 없음.
    return {
        "items": [
            {
                "id": "special_request",
                "label": "특별 요청",
                "body": "NonSmoke, LargeBed는 숙소 사정에 따라 결정됩니다.",
                "value": None,
                "evidence_state": "supported",
                "source_unit_id": "su_condition",
                "evidence_snippet": "All special requests",
            }
        ]
    }


class _SequenceJsonClient:
    """호출마다 다음 payload를 돌려준다 — order_invariant의 2회 호출을 구분해 테스트."""

    def __init__(self, payloads: list[object]) -> None:
        self._payloads = payloads
        self._calls = 0

    def generate_json(self, *, system: str, user: str) -> object:
        payload = self._payloads[min(self._calls, len(self._payloads) - 1)]
        self._calls += 1
        return payload


def _caveats_payload(*entries: tuple[str, str]) -> dict:
    return {
        "caveats": [
            {"source_unit_id": sid, "snippet": snip, "text": _CONDITION}
            for sid, snip in entries
        ]
    }


# ── extractor: per-unit caveats 목록을 파싱한다(가) ───────────────────────────
def test_extractor_parses_caveat() -> None:
    unit = _unit(unit_id="su_condition", text=_CONDITION)
    extractor = OllamaCaveatExtractor(
        client=_FakeJsonClient(
            _caveats_payload(("su_condition", "subject to availability"))
        )
    )
    candidate = answer_candidate_from_payload(
        index=1, question="질문", payload=_p1_01_style_payload()["items"][0]
    )
    assert candidate is not None

    caveat = extractor.extract(
        question="질문", candidate=candidate, context=_context(unit)
    )

    assert caveat is not None
    assert caveat.snippet == "subject to availability"


def test_extractor_returns_none_when_no_condition() -> None:
    unit = _unit(unit_id="su_condition", text=_CONDITION)
    extractor = OllamaCaveatExtractor(client=_FakeJsonClient({"caveats": []}))
    candidate = answer_candidate_from_payload(
        index=1, question="질문", payload=_p1_01_style_payload()["items"][0]
    )
    assert candidate is not None

    assert (
        extractor.extract(question="질문", candidate=candidate, context=_context(unit))
        is None
    )


# ── (라-2) order_invariant: 두 순서 모두에서 나온 caveat만 인정 ────────────────
def test_order_invariant_keeps_caveat_stable_across_orders() -> None:
    unit = _unit(unit_id="su_condition", text=_CONDITION)
    # forward·reverse 두 호출 모두 같은 unit을 caveat으로 → 인정.
    client = _SequenceJsonClient(
        [
            _caveats_payload(("su_condition", "subject to availability")),
            _caveats_payload(("su_condition", "subject to availability")),
        ]
    )
    extractor = OllamaCaveatExtractor(client=client, order_invariant=True)
    candidate = answer_candidate_from_payload(
        index=1, question="질문", payload=_p1_01_style_payload()["items"][0]
    )
    assert candidate is not None

    caveat = extractor.extract(
        question="질문", candidate=candidate, context=_context(unit)
    )

    assert caveat is not None
    assert caveat.source_unit_id == "su_condition"


def test_order_invariant_drops_caveat_unstable_across_orders() -> None:
    unit = _unit(unit_id="su_condition", text=_CONDITION)
    # forward는 caveat을 냈지만 reverse(순서 뒤집기)에선 안 냄 → noise로 보고 버린다.
    client = _SequenceJsonClient(
        [
            _caveats_payload(("su_condition", "subject to availability")),
            {"caveats": []},
        ]
    )
    extractor = OllamaCaveatExtractor(client=client, order_invariant=True)
    candidate = answer_candidate_from_payload(
        index=1, question="질문", payload=_p1_01_style_payload()["items"][0]
    )
    assert candidate is not None

    assert (
        extractor.extract(question="질문", candidate=candidate, context=_context(unit))
        is None
    )


# ── 핵심: 별도 relation pass가 P1-01의 누락을 메워 needs_review로 강등한다 ─────
def test_relation_pass_downgrades_p1_01_that_answer_call_missed() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE)
    condition_unit = _unit(unit_id="su_condition", text=_CONDITION)
    extractor = _FakeExtractor(
        Caveat(
            source_unit_id="su_condition",
            snippet="subject to availability",
            text=_CONDITION,
        )
    )

    answer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(_p1_01_style_payload()),
        caveat_extractor=extractor,
    ).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(value_unit, condition_unit),
    )

    item = answer.items[0]
    assert extractor.called is True
    assert item.evidence_state == EvidenceState.NEEDS_REVIEW
    assert item.certification is not None
    assert item.certification.reason == "limited_by_caveat"


# ── 대조: relation pass가 없으면 같은 P1-01 형태는 supported로 남는다 ──────────
# (이게 run 16에서 실제로 본 gap — 답변 호출에만 맡기면 조건칸이 비어 강등 안 됨)
def test_without_relation_pass_p1_01_style_stays_supported() -> None:
    condition_unit = _unit(unit_id="su_condition", text=_CONDITION)

    answer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(_p1_01_style_payload()),
        caveat_extractor=None,
    ).compose(
        question="NonSmoke, LargeBed는 확정된 조건이야?",
        context=_context(condition_unit),
    )

    item = answer.items[0]
    assert item.evidence_state == EvidenceState.SUPPORTED


# ── relation pass는 supported가 아니면 호출하지 않는다(불필요한 두 번째 호출 방지) ─
def test_relation_pass_skipped_when_not_supported() -> None:
    condition_unit = _unit(unit_id="su_condition", text=_CONDITION)
    payload = _p1_01_style_payload()
    payload["items"][0]["evidence_state"] = "needs_review"

    # _ExplodingExtractor가 호출되면 테스트가 실패한다.
    answer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(payload),
        caveat_extractor=_ExplodingExtractor(),
    ).compose(question="질문", context=_context(condition_unit))

    assert answer.items[0].evidence_state == EvidenceState.NEEDS_REVIEW


# ── 답변 호출이 이미 조건을 냈으면 두 번째 호출을 아낀다 ──────────────────────
def test_relation_pass_skipped_when_answer_call_already_gave_condition() -> None:
    value_unit = _unit(unit_id="su_value", text=_VALUE)
    condition_unit = _unit(unit_id="su_condition", text=_CONDITION)
    payload = _p1_01_style_payload()
    payload["items"][0]["value"] = _VALUE
    payload["items"][0]["evidence_snippet"] = _VALUE
    payload["items"][0]["source_unit_id"] = "su_value"
    payload["items"][0]["caveat"] = {
        "source_unit_id": "su_condition",
        "snippet": "subject to availability",
        "text": _CONDITION,
    }

    answer = OllamaLibraryChatAnswerComposer(
        client=_FakeJsonClient(payload),
        caveat_extractor=_ExplodingExtractor(),
    ).compose(question="질문", context=_context(value_unit, condition_unit))

    # 답변 호출이 직접 낸 조건으로 이미 강등됐고, 두 번째 호출은 일어나지 않았다.
    item = answer.items[0]
    assert item.evidence_state == EvidenceState.NEEDS_REVIEW
    assert item.certification is not None
    assert item.certification.reason == "limited_by_caveat"
