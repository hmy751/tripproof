from __future__ import annotations

from server.answers.candidate import AnswerCandidate
from server.answers.library_chat_grounding import ground_evidence_ref
from server.extraction.models import Certification, EvidenceRef, EvidenceState
from server.retrieval.models import AnswerContext, SourceUnit


def certify(*, candidate: AnswerCandidate, context: AnswerContext) -> Certification:
    """LLM 후보를 받아 코드가 final evidence state를 정한다.

    입력은 후보(값/근거 ref/proposed_state)와 retrieval 구조뿐이다. 질문 free text도
    LLM draft body 문구도 보지 않는다(AC2). 검증은 LLM 후보를 끌어올리지 않고 내리기만
    한다 — proposed_state를 ceiling으로 두고, 코드가 확신할 수 있는 구조 사실이 부족하면
    안전한 쪽으로 내린다.

    이 단계가 코드로 강제하는 것은 두 가지 mechanical check다.

    - grounding: candidate가 인용한 snippet이 원문에 실재하는가.
    - value-grounding: certified value가 그 근거에 실재하는가("확정" 같은 상태 단어를
      값으로 들고 오면 여기서 걸린다 — 단어를 읽어서가 아니라 값이 원문에 없어서다).

    "이 값을 지배하는 조건/caveat가 있는가"의 판단은 여기서 하지 않는다. 그건 의미
    분류(relation/entailment)이고, source unit kind나 page 근접으로 추정하면 실제
    문서에서 무관한 값까지 강등시킨다(`docs/implementation-notes/2026-06-29-
    certification-structural-proxy-overdowngrade/`). 그 판단은 LLM/relation extractor가
    역할로 내고 코드가 그 역할 구조를 읽는 의미 층으로 재귀속했다(04 spec의
    `구현 범위 재조정`).
    """

    proposed = candidate.proposed_state

    # LLM이 "못 찾았다"고 abstain한 것은 LLM이 판단할 자리다 — 그대로 존중한다.
    if proposed == EvidenceState.MISSING:
        return _missing(proposed=proposed, reason="candidate_missing")

    evidence_ref = _ground(candidate=candidate, context=context)

    # 후보가 확정을 주장하지 않고 검토를 요청했으면 끌어올리지 않는다(ceiling).
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

    # 여기부터는 후보가 supported를 제안한 경우다. 코드가 mechanical check로 검증한다.
    if evidence_ref is None:
        # 근거가 원문에 실재하지 않으면 supported가 될 수 없다.
        return _missing(proposed=proposed, reason="ungrounded")

    source_unit = _source_unit_by_id(
        context=context, source_unit_id=candidate.cited_source_unit_id
    )
    if source_unit is None:  # pragma: no cover - grounding이 잡혔으면 항상 존재
        return _missing(proposed=proposed, reason="ungrounded")

    # certified value 자체가 근거에 실재해야 한다.
    if candidate.value is not None and not _value_grounded(
        value=candidate.value, source_unit=source_unit
    ):
        return _needs_review(
            proposed=proposed,
            reason="value_not_grounded",
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
