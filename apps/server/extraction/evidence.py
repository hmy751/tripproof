from __future__ import annotations

from server.extraction.models import EvidenceRef
from server.retrieval.models import SourceUnit


class EvidenceGroundingError(ValueError):
    pass


def evidence_ref_from_snippet(*, source_unit: SourceUnit, snippet: str) -> EvidenceRef:
    proposed_snippet = snippet.strip()
    if not proposed_snippet:
        raise EvidenceGroundingError("Evidence snippet cannot be empty.")
    grounded_snippet = _ground_snippet(
        source_text=source_unit.text, proposed_snippet=proposed_snippet
    )
    if grounded_snippet is None:
        raise EvidenceGroundingError(
            "Evidence snippet must be an exact part of the source unit text."
        )

    return EvidenceRef(
        material_id=source_unit.material_id,
        source_unit_id=source_unit.id,
        label=source_unit.file_name,
        locator=source_unit.locator,
        snippet=grounded_snippet,
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
