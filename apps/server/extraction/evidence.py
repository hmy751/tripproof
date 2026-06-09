from __future__ import annotations

from server.extraction.models import EvidenceRef, EvidenceState, FactCandidate, FactProposal, FactTarget
from server.retrieval.models import ContextPack, SourceUnit


class EvidenceGroundingError(ValueError):
    pass


def evidence_ref_from_snippet(*, source_unit: SourceUnit, snippet: str) -> EvidenceRef:
    proposed_snippet = snippet.strip()
    if not proposed_snippet:
        raise EvidenceGroundingError("Evidence snippet cannot be empty.")
    grounded_snippet = _ground_snippet(source_text=source_unit.text, proposed_snippet=proposed_snippet)
    if grounded_snippet is None:
        raise EvidenceGroundingError("Evidence snippet must be an exact part of the source unit text.")

    return EvidenceRef(
        material_id=source_unit.material_id,
        source_unit_id=source_unit.id,
        label=source_unit.file_name,
        locator=source_unit.locator,
        snippet=grounded_snippet,
    )


def evidence_ref_from_span(*, source_unit: SourceUnit, start: int, end: int) -> EvidenceRef:
    if start < 0 or end > len(source_unit.text) or start >= end:
        raise EvidenceGroundingError("Evidence span is outside the source unit text.")
    return evidence_ref_from_snippet(source_unit=source_unit, snippet=source_unit.text[start:end])


def validate_fact_proposal(
    *,
    target: FactTarget,
    context: ContextPack,
    proposal: FactProposal,
) -> FactCandidate:
    if proposal.target_id != target.id:
        return _missing_candidate(
            target=target,
            reason="extractor가 다른 확인 항목의 후보를 반환했습니다.",
        )

    if proposal.evidence_state == EvidenceState.SUPPORTED:
        if proposal.value is None or proposal.source_unit_id is None or proposal.evidence_snippet is None:
            return _missing_candidate(
                target=target,
                reason="extractor가 근거 있음 상태에 필요한 값과 근거를 함께 반환하지 않았습니다.",
            )

        source_unit = _source_unit_by_id(context=context, source_unit_id=proposal.source_unit_id)
        if source_unit is None:
            return _missing_candidate(
                target=target,
                reason="extractor가 제시한 근거 source가 retrieval 후보에 포함되지 않았습니다.",
            )

        try:
            evidence_ref = evidence_ref_from_snippet(source_unit=source_unit, snippet=proposal.evidence_snippet)
        except EvidenceGroundingError:
            return _missing_candidate(
                target=target,
                reason="extractor가 제시한 근거 문장을 source unit 원문에서 찾지 못했습니다.",
            )

        return FactCandidate(
            id=target.id,
            label=proposal.label,
            value=proposal.value,
            evidence_state=EvidenceState.SUPPORTED,
            evidence=[evidence_ref],
            sensitive=proposal.sensitive,
            reason=proposal.reason,
        )

    return FactCandidate(
        id=target.id,
        label=proposal.label,
        value=None if proposal.evidence_state == EvidenceState.MISSING else proposal.value,
        evidence_state=proposal.evidence_state,
        evidence=[],
        sensitive=proposal.sensitive,
        reason=proposal.reason,
    )


def _source_unit_by_id(*, context: ContextPack, source_unit_id: str) -> SourceUnit | None:
    for candidate in context.candidates:
        if candidate.source_unit.id == source_unit_id:
            return candidate.source_unit
    return None


def _missing_candidate(*, target: FactTarget, reason: str) -> FactCandidate:
    return FactCandidate(
        id=target.id,
        label=target.label,
        value=None,
        evidence_state=EvidenceState.MISSING,
        reason=reason,
    )


def _ground_snippet(*, source_text: str, proposed_snippet: str) -> str | None:
    if proposed_snippet in source_text:
        return proposed_snippet

    normalized_source, source_positions = _normalize_with_positions(source_text)
    normalized_snippet, _snippet_positions = _normalize_with_positions(proposed_snippet)
    if not normalized_snippet:
        return None

    normalized_start = normalized_source.find(normalized_snippet)
    if normalized_start < 0:
        return None

    normalized_end = normalized_start + len(normalized_snippet)
    original_start = source_positions[normalized_start]
    original_end = source_positions[normalized_end - 1] + 1
    return source_text[original_start:original_end].strip()


def _normalize_with_positions(value: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    positions: list[int] = []
    previous_was_space = False

    for index, char in enumerate(value):
        if char.isspace():
            if chars and not previous_was_space:
                chars.append(" ")
                positions.append(index)
            previous_was_space = True
            continue

        chars.append(char)
        positions.append(index)
        previous_was_space = False

    if chars and chars[-1] == " ":
        chars.pop()
        positions.pop()

    return "".join(chars), positions
