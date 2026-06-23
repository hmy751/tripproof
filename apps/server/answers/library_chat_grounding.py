from __future__ import annotations

import re

from server.extraction.evidence import EvidenceGroundingError, evidence_ref_from_snippet
from server.extraction.models import EvidenceRef
from server.retrieval.models import SourceUnit


def ground_evidence_ref(
    *,
    source_unit: SourceUnit,
    evidence_snippet: str,
    value: str | None,
) -> EvidenceRef | None:
    try:
        return evidence_ref_from_snippet(
            source_unit=source_unit, snippet=evidence_snippet
        )
    except EvidenceGroundingError:
        return _fallback_evidence_ref_from_value(source_unit=source_unit, value=value)


def _fallback_evidence_ref_from_value(
    *, source_unit: SourceUnit, value: str | None
) -> EvidenceRef | None:
    if value is None:
        return None

    try:
        return evidence_ref_from_snippet(source_unit=source_unit, snippet=value)
    except EvidenceGroundingError:
        pass

    snippet = _numeric_value_window(source_text=source_unit.text, value=value)
    if snippet is None:
        return None

    try:
        return evidence_ref_from_snippet(source_unit=source_unit, snippet=snippet)
    except EvidenceGroundingError:
        return None


def _numeric_value_window(*, source_text: str, value: str) -> str | None:
    value_numbers = re.findall(r"\d+", value)
    if not value_numbers:
        return None

    source_numbers = list(re.finditer(r"\d+", source_text))
    if not source_numbers:
        return None

    normalized_value_numbers = [_normalize_number(number) for number in value_numbers]
    source_index = 0
    matched = []
    for value_number in normalized_value_numbers:
        while source_index < len(source_numbers):
            candidate = source_numbers[source_index]
            source_index += 1
            if _normalize_number(candidate.group(0)) == value_number:
                matched.append(candidate)
                break
        else:
            return None

    first = matched[0]
    last = matched[-1]
    if last.end() - first.start() > 220:
        return None

    window_start = _numeric_value_window_start(
        source_text=source_text, start=first.start()
    )
    window_end = _numeric_value_window_end(source_text=source_text, end=last.end())
    return source_text[window_start:window_end].strip()


def _numeric_value_window_start(*, source_text: str, start: int) -> int:
    fallback_start = max(0, start - 80)
    position = start
    for _line in range(4):
        previous_break = source_text.rfind("\n", 0, position)
        if previous_break < 0:
            return fallback_start
        position = previous_break
    return max(fallback_start, position + 1)


def _numeric_value_window_end(*, source_text: str, end: int) -> int:
    position = end
    unit_chars = set("년월일시분초원엔박명개")
    while position < len(source_text) and position - end < 24:
        char = source_text[position]
        if char.isspace() or char in unit_chars:
            position += 1
            continue
        break
    return position


def _normalize_number(value: str) -> str:
    stripped = value.lstrip("0")
    return stripped or "0"
