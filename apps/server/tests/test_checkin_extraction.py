from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.extraction.checkin import (
    BOOKING_CONFIRMATION_FACT_ID,
    BOOKING_CONFIRMATION_TARGET,
    CHECKIN_START_TIME_FACT_ID,
    CHECKIN_START_TIME_TARGET,
    OllamaCheckinFactProposer,
    extract_checkin_fact_candidates,
)
from server.extraction.evidence import EvidenceGroundingError, evidence_ref_from_snippet, validate_fact_proposal
from server.extraction.models import EvidenceState, FactProposal
from server.llm.ollama import OllamaClientError
from server.extraction.sensitive import SensitiveKind, detect_sensitive_findings
from server.materials.store import MaterialStore
from server.retrieval.models import ContextPack, RetrievalCandidate, SourceUnit
from server.retrieval.search import retrieve_context


def test_retrieval_context_is_candidate_not_evidence() -> None:
    unit = _source_unit("체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해 주세요.")

    context = retrieve_context(
        target_id=BOOKING_CONFIRMATION_FACT_ID,
        query="예약 확정서 제시",
        source_units=[unit],
        embedding_records=[],
    )

    assert len(context.candidates) == 1
    assert context.candidates[0].source_unit == unit
    assert not hasattr(context.candidates[0], "evidence")


def test_fact_candidate_grounds_booking_confirmation_evidence() -> None:
    unit = _source_unit(
        "Booking Confirmation\n"
        "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다."
    )

    facts = extract_checkin_fact_candidates(
        source_units=[unit],
        embedding_records=[],
        proposer=_TargetProposalProposer(
            {
                BOOKING_CONFIRMATION_FACT_ID: (
                    "예약 확정서(전자 사본 또는 인쇄본)",
                    "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다.",
                )
            }
        ),
    )
    fact = _fact_by_id(facts, BOOKING_CONFIRMATION_FACT_ID)

    assert fact.evidence_state == EvidenceState.SUPPORTED
    assert "예약 확정서" in (fact.value or "")
    assert len(fact.evidence) == 1
    assert fact.evidence[0].snippet in unit.text
    assert fact.evidence[0].locator == "booking.pdf p.1 u.1"


def test_validator_downgrades_supported_proposal_when_snippet_is_not_grounded() -> None:
    unit = _source_unit("체크인 시 예약 확정서를 제시해 주세요.")
    context = ContextPack(
        target_id=BOOKING_CONFIRMATION_FACT_ID,
        query="예약 확정서 제시",
        candidates=[
            RetrievalCandidate(
                target_id=BOOKING_CONFIRMATION_FACT_ID,
                query="예약 확정서 제시",
                source_unit=unit,
                score=1.0,
                lexical_score=1,
                vector_score=None,
            )
        ],
    )
    proposal = FactProposal(
        target_id=BOOKING_CONFIRMATION_FACT_ID,
        label="예약 확정서 제시",
        value="예약 확정서 전자 사본",
        evidence_state=EvidenceState.SUPPORTED,
        evidence_snippet="원문에 없는 근거 문장",
        source_unit_id=unit.id,
    )

    fact = validate_fact_proposal(target=BOOKING_CONFIRMATION_TARGET, context=context, proposal=proposal)

    assert fact.evidence_state == EvidenceState.MISSING
    assert fact.value is None
    assert fact.evidence == []


def test_checkin_start_time_stays_missing_when_pdf_only_has_arrival_date() -> None:
    unit = _source_unit(
        "Arrival :\n"
        "체크인 :\n"
        "2025년 3월 09일\n"
        "Booking Confirmation\n"
        "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다."
    )

    facts = extract_checkin_fact_candidates(
        source_units=[unit],
        embedding_records=[],
        proposer=_TargetProposalProposer(),
    )
    fact = _fact_by_id(facts, CHECKIN_START_TIME_FACT_ID)

    assert fact.evidence_state == EvidenceState.MISSING
    assert fact.value is None
    assert fact.evidence == []


def test_checkin_start_time_is_supported_only_when_time_text_is_grounded() -> None:
    unit = _source_unit("체크인은 15:00부터 가능합니다. 예약 확정서를 제시해 주세요.")

    facts = extract_checkin_fact_candidates(
        source_units=[unit],
        embedding_records=[],
        proposer=_TargetProposalProposer(
            {
                CHECKIN_START_TIME_FACT_ID: (
                    "15:00",
                    "체크인은 15:00부터 가능합니다.",
                )
            }
        ),
    )
    fact = _fact_by_id(facts, CHECKIN_START_TIME_FACT_ID)

    assert fact.evidence_state == EvidenceState.SUPPORTED
    assert fact.value == "15:00"
    assert len(fact.evidence) == 1
    assert fact.evidence[0].snippet in unit.text


def test_booking_confirmation_stays_missing_without_grounded_source() -> None:
    unit = _source_unit("체크인 날짜는 2025년 3월 09일입니다.")

    facts = extract_checkin_fact_candidates(
        source_units=[unit],
        embedding_records=[],
        proposer=_TargetProposalProposer(),
    )
    fact = _fact_by_id(facts, BOOKING_CONFIRMATION_FACT_ID)

    assert fact.evidence_state == EvidenceState.MISSING
    assert fact.value is None
    assert fact.evidence == []


def test_evidence_ref_rejects_snippets_outside_source_unit_text() -> None:
    unit = _source_unit("Show your booking confirmation.")

    with pytest.raises(EvidenceGroundingError):
        evidence_ref_from_snippet(source_unit=unit, snippet="Show your passport.")


def test_evidence_ref_grounds_whitespace_normalized_snippet_to_source_text() -> None:
    unit = _source_unit("체크인 시\n고객님의 예약 확정서를\n제시해 주세요.")

    evidence = evidence_ref_from_snippet(
        source_unit=unit,
        snippet="체크인 시 고객님의 예약 확정서를 제시해 주세요.",
    )

    assert evidence.snippet in unit.text
    assert "\n" in evidence.snippet


def test_sensitive_fields_are_detected_without_becoming_supported_facts() -> None:
    unit = _source_unit(
        "Booking ID : [BOOKING_ID]\n"
        "Client : [GUEST_NAME]\n"
        "카드 번호 : [PAYMENT_CARD]\n"
        "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다."
    )

    findings = detect_sensitive_findings([unit])
    facts = extract_checkin_fact_candidates(
        source_units=[unit],
        embedding_records=[],
        proposer=_TargetProposalProposer(
            {
                BOOKING_CONFIRMATION_FACT_ID: (
                    "예약 확정서(전자 사본 또는 인쇄본)",
                    "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다.",
                )
            }
        ),
    )

    assert {finding.kind for finding in findings} >= {
        SensitiveKind.BOOKING_ID,
        SensitiveKind.GUEST_NAME,
        SensitiveKind.PAYMENT_CARD,
    }
    assert {fact.id for fact in facts} == {BOOKING_CONFIRMATION_FACT_ID, CHECKIN_START_TIME_FACT_ID}
    assert all(not fact.sensitive for fact in facts)


def test_question_response_includes_evidence_backed_fact_candidates() -> None:
    store = MaterialStore()
    material = store.add_ready(
        name="Agoda Fukuoka",
        file_name="booking.pdf",
        content_type="application/pdf",
        page_count=1,
        text=(
            "[page 1]\n"
            "Arrival : 체크인 : 2025년 3월 09일\n"
            "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다."
        ),
        preview="체크인 시 고객님의 예약 확정서",
    )
    client = TestClient(
        create_app(
            store=store,
            checkin_fact_proposer=_TargetProposalProposer(
                {
                    BOOKING_CONFIRMATION_FACT_ID: (
                        "예약 확정서(전자 사본 또는 인쇄본)",
                        "체크인 시 고객님의 예약 확정서(전자 사본 또는 인쇄본)를 제시해 주시기 바랍니다.",
                    )
                }
            ),
        )
    )

    response = client.post("/api/questions", json={"question": "체크인 때 뭘 보여줘?", "materialIds": [material.id]})

    assert response.status_code == 200
    body = response.json()
    answer_items = {item["id"]: item for item in body["answer"]["items"]}
    assert "확인한 내용과 확인되지 않은 항목" in body["answer"]["summary"]
    assert answer_items[BOOKING_CONFIRMATION_FACT_ID]["evidenceState"] == "supported"
    assert "예약 확정서" in answer_items[BOOKING_CONFIRMATION_FACT_ID]["body"]
    assert answer_items[BOOKING_CONFIRMATION_FACT_ID]["evidence"][0]["snippet"]
    assert answer_items[CHECKIN_START_TIME_FACT_ID]["evidenceState"] == "missing"
    assert answer_items[CHECKIN_START_TIME_FACT_ID]["value"] is None
    assert "체크인 시작 시각을 확인하지 못했습니다" in answer_items[CHECKIN_START_TIME_FACT_ID]["body"]
    assert answer_items[CHECKIN_START_TIME_FACT_ID]["evidence"] == []
    assert "excerpt" not in body
    assert "facts" not in body


def test_ollama_checkin_proposer_maps_structured_json_to_grounded_fact() -> None:
    unit = _source_unit("체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해 주세요.")
    context = _context_for_target(target_id=BOOKING_CONFIRMATION_FACT_ID, unit=unit)
    proposer = OllamaCheckinFactProposer(
        client=_FakeJsonClient(
            {
                "target_id": BOOKING_CONFIRMATION_FACT_ID,
                "label": "예약 확정서 제시",
                "value": "예약 확정서 전자 사본 또는 인쇄본",
                "evidence_state": "supported",
                "source_unit_id": unit.id,
                "evidence_snippet": "체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해 주세요.",
                "sensitive": False,
                "reason": "원문에 예약 확정서 제시 안내가 있습니다.",
            }
        )
    )

    proposal = proposer.propose(target=BOOKING_CONFIRMATION_TARGET, context=context)
    fact = validate_fact_proposal(target=BOOKING_CONFIRMATION_TARGET, context=context, proposal=proposal)

    assert fact.evidence_state == EvidenceState.SUPPORTED
    assert fact.value == "예약 확정서 전자 사본 또는 인쇄본"
    assert fact.evidence[0].snippet in unit.text


def test_ollama_checkin_proposer_repairs_paraphrased_booking_snippet_to_narrow_evidence() -> None:
    unit = _source_unit(
        "Booking ID : [BOOKING_ID]\n"
        "Client : [GUEST_NAME]\n"
        "Booking Confirmation\n"
        "체크인\n"
        "시\n"
        "고객님의\n"
        "예약\n"
        "확정서\n"
        "(\n"
        "전자\n"
        "사본\n"
        "또는\n"
        "인쇄본\n"
        ")\n"
        "를\n"
        "제시해\n"
        "주시기\n"
        "바랍니다\n"
        ".\n"
        "Address : [EXACT_ADDRESS]\n"
        "Property Contact Number : [PHONE_NUMBER]"
    )
    context = _context_for_target(target_id=BOOKING_CONFIRMATION_FACT_ID, unit=unit)
    proposer = OllamaCheckinFactProposer(
        client=_FakeJsonClient(
            {
                "target_id": BOOKING_CONFIRMATION_FACT_ID,
                "label": "예약 확정서 제시",
                "value": "예약 확정서 제시",
                "evidence_state": "supported",
                "source_unit_id": unit.id,
                "evidence_snippet": "예약 확정서를 보여줘야 합니다.",
                "sensitive": False,
                "reason": "원문에 예약 확정서 제시 안내가 있습니다.",
            }
        )
    )

    proposal = proposer.propose(target=BOOKING_CONFIRMATION_TARGET, context=context)
    fact = validate_fact_proposal(target=BOOKING_CONFIRMATION_TARGET, context=context, proposal=proposal)

    assert fact.evidence_state == EvidenceState.SUPPORTED
    assert fact.evidence[0].snippet != unit.text
    assert "예약\n확정서" in fact.evidence[0].snippet
    assert "[BOOKING_ID]" not in fact.evidence[0].snippet
    assert "[GUEST_NAME]" not in fact.evidence[0].snippet
    assert "[EXACT_ADDRESS]" not in fact.evidence[0].snippet
    assert "[PHONE_NUMBER]" not in fact.evidence[0].snippet


def test_ollama_checkin_proposer_returns_missing_when_client_fails() -> None:
    unit = _source_unit("체크인은 15:00부터 가능합니다.")
    context = _context_for_target(target_id=CHECKIN_START_TIME_FACT_ID, unit=unit)
    proposer = OllamaCheckinFactProposer(client=_FailingJsonClient())

    proposal = proposer.propose(target=CHECKIN_START_TIME_TARGET, context=context)

    assert proposal.evidence_state == EvidenceState.MISSING
    assert proposal.value is None


def test_ollama_checkin_proposer_does_not_accept_date_as_checkin_start_time() -> None:
    unit = _source_unit("Arrival : 체크인 : 2025년 3월 09일")
    context = _context_for_target(target_id=CHECKIN_START_TIME_FACT_ID, unit=unit)
    proposer = OllamaCheckinFactProposer(
        client=_FakeJsonClient(
            {
                "target_id": CHECKIN_START_TIME_FACT_ID,
                "label": "체크인 시작 시각",
                "value": "2025년 3월 09일",
                "evidence_state": "supported",
                "source_unit_id": unit.id,
                "evidence_snippet": "Arrival : 체크인 : 2025년 3월 09일",
                "sensitive": False,
                "reason": "원문에 체크인 날짜가 있습니다.",
            }
        )
    )

    proposal = proposer.propose(target=CHECKIN_START_TIME_TARGET, context=context)

    assert proposal.evidence_state == EvidenceState.MISSING
    assert proposal.value is None


def _fact_by_id(facts, fact_id: str):
    return next(fact for fact in facts if fact.id == fact_id)


def _source_unit(text: str) -> SourceUnit:
    return SourceUnit(
        id="su_mat_1_1",
        material_id="mat_1",
        file_name="booking.pdf",
        page=1,
        unit_index=1,
        locator="booking.pdf p.1 u.1",
        text=text,
        search_text=text,
        start=0,
        end=len(text),
    )


def _context_for_target(*, target_id: str, unit: SourceUnit) -> ContextPack:
    return ContextPack(
        target_id=target_id,
        query="test query",
        candidates=[
            RetrievalCandidate(
                target_id=target_id,
                query="test query",
                source_unit=unit,
                score=1.0,
                lexical_score=1,
                vector_score=None,
            )
        ],
    )


class _TargetProposalProposer:
    def __init__(self, supported: dict[str, tuple[str, str]] | None = None) -> None:
        self._supported = supported or {}

    def propose(self, *, target, context):
        supported = self._supported.get(target.id)
        if supported is None:
            return FactProposal(
                target_id=target.id,
                label=target.label,
                value=None,
                evidence_state=EvidenceState.MISSING,
                reason="테스트 proposer가 해당 항목을 missing으로 반환했습니다.",
            )

        value, snippet = supported
        source_unit = next(
            (candidate.source_unit for candidate in context.candidates if snippet in candidate.source_unit.text),
            None,
        )
        return FactProposal(
            target_id=target.id,
            label=target.label,
            value=value,
            evidence_state=EvidenceState.SUPPORTED,
            evidence_snippet=snippet,
            source_unit_id=source_unit.id if source_unit else None,
            reason="테스트 proposer가 명시된 근거 후보를 반환했습니다.",
        )


class _FakeJsonClient:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def generate_json(self, *, system: str, user: str) -> object:
        return self._payload


class _FailingJsonClient:
    def generate_json(self, *, system: str, user: str) -> object:
        raise OllamaClientError("test failure")
