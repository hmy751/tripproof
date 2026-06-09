from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol

from server.extraction.evidence import validate_fact_proposal
from server.extraction.models import EvidenceState, FactCandidate, FactProposal, FactTarget
from server.retrieval.embeddings import EmbeddingProvider
from server.retrieval.models import ContextPack, EmbeddingRecord, SourceUnit
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

_BOOKING_CONFIRMATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"예약\s*확정서.{0,80}(전자\s*사본|인쇄본).{0,80}제시[가-힣\s]*바랍니다",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"booking\s*confirmation.{0,160}(electronic|paper|printed|printout).{0,160}(present|show)",
        re.IGNORECASE | re.DOTALL,
    ),
)

_CHECKIN_START_TIME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"check[-\s]?in.{0,80}?(starts?|from|time).{0,40}?(?P<value>[0-2]?\d:[0-5]\d)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"체크인.{0,40}?(시작|시간|가능|부터).{0,40}?(?P<value>[0-2]?\d\s*:\s*[0-5]\d)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"체크인.{0,40}?(?P<value>[0-2]?\d\s*:\s*[0-5]\d).{0,20}?(부터|시작|가능)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"체크인.{0,40}?(?P<value>[0-2]?\d\s*시).{0,20}?(부터|시작|가능)",
        re.IGNORECASE | re.DOTALL,
    ),
)


class CheckinFactProposer(Protocol):
    def propose(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        """Propose a fact candidate from retrieved source text.

        A later LLM structured-output adapter can implement this protocol. The
        proposal is never accepted until the validator grounds its snippet in
        SourceUnit.text.
        """


class LocalCheckinFactProposer:
    def propose(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        if target.id == BOOKING_CONFIRMATION_FACT_ID:
            return self._booking_confirmation_proposal(target=target, context=context)
        if target.id == CHECKIN_START_TIME_FACT_ID:
            return self._checkin_start_time_proposal(target=target, context=context)
        return _missing_proposal(target=target, reason="지원하지 않는 체크인 확인 항목입니다.")

    def _booking_confirmation_proposal(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        for candidate in context.candidates:
            match = _first_match(candidate.source_unit.text, _BOOKING_CONFIRMATION_PATTERNS)
            if match is None:
                continue
            snippet = match.group(0).strip()
            return FactProposal(
                target_id=target.id,
                label=target.label,
                value=_compact_text(snippet),
                evidence_state=EvidenceState.SUPPORTED,
                evidence_snippet=snippet,
                source_unit_id=candidate.source_unit.id,
                reason="retrieval 후보 원문에서 예약 확정서 제시 안내 후보를 찾았습니다.",
            )
        return _missing_proposal(
            target=target,
            reason="현재 등록된 자료에서 체크인 시 예약 확정서 제시 안내 후보를 찾지 못했습니다.",
        )

    def _checkin_start_time_proposal(self, *, target: FactTarget, context: ContextPack) -> FactProposal:
        for candidate in context.candidates:
            match = _first_match(candidate.source_unit.text, _CHECKIN_START_TIME_PATTERNS)
            if match is None:
                continue
            snippet = match.group(0).strip()
            return FactProposal(
                target_id=target.id,
                label=target.label,
                value=_normalize_time_value(match.group("value")),
                evidence_state=EvidenceState.SUPPORTED,
                evidence_snippet=snippet,
                source_unit_id=candidate.source_unit.id,
                reason="retrieval 후보 원문에서 체크인 시작 시각 후보를 찾았습니다.",
            )
        return _missing_proposal(
            target=target,
            reason="현재 등록된 자료에서 체크인 시작 시각 후보를 찾지 못했습니다.",
        )


def extract_checkin_fact_candidates(
    *,
    source_units: Iterable[SourceUnit],
    embedding_records: Iterable[EmbeddingRecord],
    embedding_provider: EmbeddingProvider | None = None,
    proposer: CheckinFactProposer | None = None,
) -> list[FactCandidate]:
    units = list(source_units)
    records = list(embedding_records)
    active_proposer = proposer or LocalCheckinFactProposer()
    candidates: list[FactCandidate] = []

    for target in CHECKIN_FACT_TARGETS:
        context = retrieve_context(
            target_id=target.id,
            query=target.query,
            source_units=units,
            embedding_records=records,
            embedding_provider=embedding_provider,
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


def _first_match(text: str, patterns: tuple[re.Pattern[str], ...]) -> re.Match[str] | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match is not None:
            return match
    return None


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_time_value(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())
