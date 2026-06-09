from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from server.core.config import (
    FACT_PROPOSER_BACKEND,
    OLLAMA_BASE_URL,
    OLLAMA_FACT_MODEL,
    OLLAMA_FACT_TIMEOUT_SECONDS,
)
from server.extraction.evidence import EvidenceGroundingError, evidence_ref_from_snippet, validate_fact_proposal
from server.extraction.models import EvidenceState, FactCandidate, FactProposal, FactTarget
from server.llm.ollama import OllamaChatJsonClient, OllamaChatJsonConfig, OllamaClientError
from server.retrieval.embeddings import EmbeddingProvider
from server.retrieval.models import ContextPack, EmbeddingRecord, SourceUnit
from server.retrieval.repository import RetrievalRepository
from server.retrieval.search import retrieve_context

BOOKING_CONFIRMATION_FACT_ID = "checkin_booking_confirmation"
CHECKIN_START_TIME_FACT_ID = "checkin_start_time"

BOOKING_CONFIRMATION_TARGET = FactTarget(
    id=BOOKING_CONFIRMATION_FACT_ID,
    label="예약 확정서 제시",
    query="예약 확정서 전자 사본 인쇄본 제시 booking confirmation electronic printed present show",
)
CHECKIN_START_TIME_TARGET = FactTarget(
    id=CHECKIN_START_TIME_FACT_ID,
    label="체크인 시작 시각",
    query="체크인 시작 시각 시간 check-in starts from time",
)
CHECKIN_FACT_TARGETS = (BOOKING_CONFIRMATION_TARGET, CHECKIN_START_TIME_TARGET)


class CheckinFactProposer(Protocol):
    def propose(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        """Propose a fact candidate from retrieved source text.

        The proposal is never accepted until the validator grounds its snippet
        in SourceUnit.text.
        """


class MissingCheckinFactProposer:
    def __init__(self, *, reason: str = "fact proposer가 비활성화되어 후보를 만들지 않았습니다.") -> None:
        self._reason = reason

    def propose(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        return _missing_proposal(target=target, reason=self._reason)


class OllamaCheckinFactProposer:
    def __init__(self, *, client: OllamaChatJsonClient) -> None:
        self._client = client

    def propose(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        if not context.candidates:
            return _missing_proposal(target=target, reason="retrieval 후보가 없어 fact 후보를 만들지 않았습니다.")

        try:
            payload = self._client.generate_json(
                system=_system_prompt(),
                user=_user_prompt(target=target, context=context),
            )
        except OllamaClientError as exc:
            return _missing_proposal(target=target, reason=f"LLM proposer 호출에 실패했습니다: {exc}")

        proposal = _proposal_from_payload(target=target, payload=payload)
        return _repair_supported_proposal(target=target, context=context, proposal=proposal)


def create_checkin_fact_proposer_from_config(
    *,
    backend: str | None = None,
) -> CheckinFactProposer:
    active_backend = (backend or FACT_PROPOSER_BACKEND).lower()
    if active_backend == "ollama":
        return OllamaCheckinFactProposer(
            client=OllamaChatJsonClient(
                OllamaChatJsonConfig(
                    base_url=OLLAMA_BASE_URL,
                    model=OLLAMA_FACT_MODEL,
                    timeout_seconds=OLLAMA_FACT_TIMEOUT_SECONDS,
                )
            )
        )
    if active_backend in {"disabled", "missing"}:
        return MissingCheckinFactProposer()
    raise ValueError(f"Unsupported check-in fact proposer backend: {active_backend}")


def extract_checkin_fact_candidates(
    *,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None = None,
    retrieval_repository: RetrievalRepository | None = None,
    material_ids: Iterable[str] | None = None,
    proposer: CheckinFactProposer | None = None,
) -> list[FactCandidate]:
    units = list(source_units)
    records = list(embedding_records)
    active_proposer = proposer or create_checkin_fact_proposer_from_config()
    candidates: list[FactCandidate] = []

    for target in CHECKIN_FACT_TARGETS:
        context = retrieve_context(
            target_id=target.id,
            query=target.query,
            source_units=units,
            embedding_records=records,
            embedding_provider=embedding_provider,
            retrieval_repository=retrieval_repository,
            material_ids=material_ids,
        )
        proposal = active_proposer.propose(target=target, context=context)
        candidates.append(validate_fact_proposal(target=target, context=context, proposal=proposal))

    return candidates


def _missing_proposal(*, target: FactTarget, reason: str) -> FactProposal:
    return FactProposal(
        target_id=target.id,
        label=target.label,
        value=None,
        evidence_state=EvidenceState.MISSING,
        reason=reason,
    )


def _system_prompt() -> str:
    return (
        "You extract evidence-backed accommodation check-in facts from retrieved source units. "
        "Use only the provided source unit text. Do not infer from general travel knowledge. "
        "Return JSON only."
    )


def _user_prompt(*, target: FactTarget, context: ContextPack) -> str:
    guidance = _target_guidance(target)
    source_blocks = "\n\n".join(
        (
            f"source_unit_id: {candidate.source_unit.id}\n"
            f"locator: {candidate.source_unit.locator}\n"
            f"text:\n{candidate.source_unit.text}"
        )
        for candidate in context.candidates
    )
    return (
        f"target_id: {target.id}\n"
        f"target_label: {target.label}\n"
        f"target_query: {target.query}\n"
        f"guidance: {guidance}\n\n"
        "Return this JSON shape exactly:\n"
        "{\n"
        '  "target_id": "string",\n'
        '  "label": "string",\n'
        '  "value": "string or null",\n'
        '  "evidence_state": "supported | missing | needs_review",\n'
        '  "source_unit_id": "string or null",\n'
        '  "evidence_snippet": "string or null",\n'
        '  "sensitive": false,\n'
        '  "reason": "Korean sentence"\n'
        "}\n\n"
        "If evidence_state is supported, source_unit_id must be one of the provided ids and "
        "evidence_snippet must be an exact substring copied from that source unit text. "
        "If no exact source text supports the value, use evidence_state missing and value null.\n\n"
        f"Retrieved source units:\n{source_blocks}"
    )


def _target_guidance(target: FactTarget) -> str:
    if target.id == BOOKING_CONFIRMATION_FACT_ID:
        return (
            "Find whether the guest must present or show a booking confirmation, reservation confirmation, "
            "electronic copy, printed copy, paper copy, or printout during check-in."
        )
    if target.id == CHECKIN_START_TIME_FACT_ID:
        return (
            "Extract a check-in start time only when an explicit time is present, such as 15:00 or 3 PM. "
            "Do not treat arrival date, check-in date, check-out time, or general check-in wording as a start time."
        )
    return "Extract only the target fact if it is directly supported by source text."


def _proposal_from_payload(*, target: FactTarget, payload: object) -> FactProposal:
    if not isinstance(payload, dict):
        return _missing_proposal(target=target, reason="LLM proposer가 JSON object를 반환하지 않았습니다.")

    evidence_state = _evidence_state_from_value(_field(payload, "evidence_state", "evidenceState"))
    if evidence_state is None:
        return _missing_proposal(target=target, reason="LLM proposer가 지원하지 않는 evidence_state를 반환했습니다.")

    value = _optional_string(_field(payload, "value"))
    evidence_snippet = _optional_string(_field(payload, "evidence_snippet", "evidenceSnippet"))
    source_unit_id = _optional_string(_field(payload, "source_unit_id", "sourceUnitId"))
    reason = _optional_string(_field(payload, "reason")) or "LLM proposer가 fact 후보를 반환했습니다."
    sensitive = bool(_field(payload, "sensitive") is True)

    if target.id == CHECKIN_START_TIME_FACT_ID and evidence_state == EvidenceState.SUPPORTED:
        if value is None or not _looks_like_time_value(value):
            return _missing_proposal(
                target=target,
                reason="LLM proposer가 체크인 시작 시각을 실제 시간 값으로 반환하지 않았습니다.",
            )

    return FactProposal(
        target_id=_optional_string(_field(payload, "target_id", "targetId")) or target.id,
        label=_optional_string(_field(payload, "label")) or target.label,
        value=value,
        evidence_state=evidence_state,
        evidence_snippet=evidence_snippet,
        source_unit_id=source_unit_id,
        sensitive=sensitive,
        reason=reason,
    )


def _repair_supported_proposal(
    *,
    target: FactTarget,
    context: ContextPack,
    proposal: FactProposal,
) -> FactProposal:
    if proposal.evidence_state != EvidenceState.SUPPORTED or proposal.source_unit_id is None:
        return proposal

    source_unit = _source_unit_by_id(context=context, source_unit_id=proposal.source_unit_id)
    if source_unit is None:
        return proposal

    if proposal.evidence_snippet is not None:
        try:
            evidence_ref = evidence_ref_from_snippet(source_unit=source_unit, snippet=proposal.evidence_snippet)
            return FactProposal(
                target_id=proposal.target_id,
                label=proposal.label,
                value=proposal.value,
                evidence_state=proposal.evidence_state,
                evidence_snippet=evidence_ref.snippet,
                source_unit_id=proposal.source_unit_id,
                sensitive=proposal.sensitive,
                reason=proposal.reason,
            )
        except EvidenceGroundingError:
            pass

    if target.id != BOOKING_CONFIRMATION_FACT_ID or not source_unit.text.strip():
        return proposal

    return FactProposal(
        target_id=proposal.target_id,
        label=proposal.label,
        value=proposal.value,
        evidence_state=proposal.evidence_state,
        evidence_snippet=source_unit.text.strip(),
        source_unit_id=proposal.source_unit_id,
        sensitive=proposal.sensitive,
        reason=proposal.reason,
    )


def _source_unit_by_id(*, context: ContextPack, source_unit_id: str) -> SourceUnit | None:
    for candidate in context.candidates:
        if candidate.source_unit.id == source_unit_id:
            return candidate.source_unit
    return None


def _evidence_state_from_value(value: object) -> EvidenceState | None:
    if not isinstance(value, str):
        return None
    try:
        return EvidenceState(value.strip().lower())
    except ValueError:
        return None


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


def _looks_like_time_value(value: str) -> bool:
    lower_value = value.strip().lower()
    if not any(char.isdigit() for char in lower_value):
        return False
    return ":" in lower_value or "시" in lower_value or "am" in lower_value or "pm" in lower_value
