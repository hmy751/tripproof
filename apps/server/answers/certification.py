from __future__ import annotations

from server.answers.candidate import AnswerCandidate
from server.answers.library_chat_grounding import ground_evidence_ref
from server.extraction.models import Certification, EvidenceRef, EvidenceState
from server.retrieval.models import AnswerContext, SourceUnit

# 조건/정책/주의/비용처럼 "값의 존재"만으로 행동 판단을 확정할 수 없게 만드는 kind.
# 이 kind는 lexical annotation(_semantic_kind)에서 올 수 있으므로 "이 kind가
# 보이면 강등"이라는 탐지에만 기대지 않는다. 핵심 계약은 반대 방향이다:
# supported가 되려면 구조적 정당화가 있어야 하고, 신호가 없거나 애매하면 default가
# 위험한 supported가 아니라 needs_review다.
CONDITIONAL_KINDS: frozenset[str] = frozenset(
    {"policy", "warning", "request_note", "fee"}
)


def certify(*, candidate: AnswerCandidate, context: AnswerContext) -> Certification:
    """LLM 후보를 받아 코드가 final evidence state를 정한다.

    입력은 후보(값/근거 ref/proposed_state)와 retrieval 구조뿐이다. 질문 free text도
    LLM draft body 문구도 보지 않는다(AC2). 판정 기준은 단어가 아니라 구조다:
    grounded 여부, certified value가 근거에 실재하는지, 인용한 source unit의
    `kind`, 그리고 같은 자리에 조건/caveat kind 근거가 함께 있는지.

    검증은 LLM 후보를 끌어올리지 않고 내리기만 한다(생성과 검증 분리). 후보가 제안한
    상태를 ceiling으로 두고, 구조가 충분히 정당화하지 못하면 안전한 쪽으로 내린다.
    """

    proposed = candidate.proposed_state

    # LLM이 "못 찾았다"고 abstain한 것은 LLM이 판단할 자리다 — 그대로 존중한다.
    if proposed == EvidenceState.MISSING:
        return _missing(proposed=proposed, reason="candidate_missing")

    evidence_ref = _ground(candidate=candidate, context=context)

    # 후보가 확정을 주장하지 않고 검토를 요청했으면, grounding 여부와 무관하게
    # 끌어올리지 않는다. 근거가 잡히면 함께 보존해 사용자가 값을 볼 수 있게 둔다.
    if proposed == EvidenceState.NEEDS_REVIEW:
        return _needs_review(
            proposed=proposed,
            reason="candidate_needs_review",
            evidence_ref=evidence_ref,
        )
    if proposed == EvidenceState.CONFLICT:
        # conflict dispatch/prompt 라우팅은 아직 미구현 — 안전하게 검토로 보낸다.
        return _needs_review(
            proposed=proposed,
            reason="candidate_conflict",
            evidence_ref=evidence_ref,
        )

    # 여기부터는 후보가 supported를 제안한 경우다. 코드가 구조로 다시 정당화한다.
    if evidence_ref is None:
        # 근거가 원문에 실재하지 않으면 supported가 될 수 없다(AC: evidence snippet과
        # source reference가 없으면 supported 불가).
        return _missing(proposed=proposed, reason="ungrounded")

    source_unit = _source_unit_by_id(
        context=context, source_unit_id=candidate.cited_source_unit_id
    )
    if source_unit is None:  # pragma: no cover - grounding이 잡혔으면 항상 존재
        return _missing(proposed=proposed, reason="ungrounded")

    # certified value 자체가 근거에 실재해야 한다. "확정" 같은 상태 단어를 value로
    # 들고 오면 여기서 잡힌다(근거에 없으므로). 단어를 읽어 막는 게 아니라, 값이
    # 근거로 grounding되는지라는 구조 사실로 막는다.
    if candidate.value is not None and not _value_grounded(
        value=candidate.value, source_unit=source_unit
    ):
        return _needs_review(
            proposed=proposed,
            reason="value_not_grounded",
            evidence_ref=evidence_ref,
        )

    cited_kind = _kind(source_unit)

    # 인용한 source unit 자체가 조건/정책/주의/비용 kind면, 그 자료는 본질적으로
    # 조건부다. 값-only 인용으로 전체를 확정(supported)할 수 없다(AC6).
    if cited_kind in CONDITIONAL_KINDS:
        return _needs_review(
            proposed=proposed,
            reason="conditional_source_kind",
            evidence_ref=evidence_ref,
        )

    # 값 근거와 조건/caveat 근거가 분리돼 같은 자리(같은 page)에 함께 있으면,
    # value-only 인용만으로 행동 판단을 확정하지 않는다(AC3/AC4). 조건을 인용에
    # 함께 reconcile하지 않은 채 값만 든 경우다.
    if _has_colocated_condition(context=context, cited=source_unit):
        return _needs_review(
            proposed=proposed,
            reason="value_only_with_condition",
            evidence_ref=evidence_ref,
        )

    return Certification(
        state=EvidenceState.SUPPORTED,
        reason="grounded_value",
        proposed_state=proposed,
        evidence=[evidence_ref],
    )


# ── helpers ─────────────────────────────────────────────────────────────────
def _ground(
    *, candidate: AnswerCandidate, context: AnswerContext
) -> EvidenceRef | None:
    if candidate.cited_source_unit_id is None or candidate.evidence_snippet is None:
        return None
    source_unit = _source_unit_by_id(
        context=context, source_unit_id=candidate.cited_source_unit_id
    )
    if source_unit is None:
        return None
    return ground_evidence_ref(
        source_unit=source_unit,
        evidence_snippet=candidate.evidence_snippet,
        value=candidate.value,
    )


def _value_grounded(*, value: str, source_unit: SourceUnit) -> bool:
    return (
        ground_evidence_ref(
            source_unit=source_unit, evidence_snippet=value, value=value
        )
        is not None
    )


def _kind(source_unit: SourceUnit) -> str:
    kind = source_unit.metadata.get("kind")
    if isinstance(kind, str) and kind:
        return kind
    return "general"


def _has_colocated_condition(*, context: AnswerContext, cited: SourceUnit) -> bool:
    for candidate in context.candidates:
        unit = candidate.source_unit
        if unit.id == cited.id:
            continue
        if unit.page != cited.page:
            continue
        if _kind(unit) in CONDITIONAL_KINDS:
            return True
    return False


def _source_unit_by_id(
    *, context: AnswerContext, source_unit_id: str | None
) -> SourceUnit | None:
    if source_unit_id is None:
        return None
    for candidate in context.candidates:
        if candidate.source_unit.id == source_unit_id:
            return candidate.source_unit
    return None


def _missing(*, proposed: EvidenceState, reason: str) -> Certification:
    return Certification(
        state=EvidenceState.MISSING,
        reason=reason,
        proposed_state=proposed,
        evidence=[],
    )


def _needs_review(
    *, proposed: EvidenceState, reason: str, evidence_ref: EvidenceRef | None
) -> Certification:
    return Certification(
        state=EvidenceState.NEEDS_REVIEW,
        reason=reason,
        proposed_state=proposed,
        evidence=[evidence_ref] if evidence_ref is not None else [],
    )
