from __future__ import annotations

from dataclasses import dataclass

from server.extraction.models import EvidenceState


@dataclass(frozen=True)
class NormalizedAnswerItemPayload:
    raw: dict[object, object]
    evidence_state: EvidenceState
    label: str
    body: str
    value: str | None
    source_unit_id: str | None
    evidence_snippet: str | None

    def response_id(self, *, index: int) -> str:
        return _item_id(payload=self.raw, index=index)


def normalize_answer_item_payload(
    *,
    question: str,
    payload: object,
) -> NormalizedAnswerItemPayload | None:
    if not isinstance(payload, dict):
        return None

    value = _optional_string(_field(payload, "value"))
    label = _display_label(
        raw_label=_optional_string(_field(payload, "label")), value=value
    )
    body = _display_body(
        question=question,
        label=label,
        body=_optional_string(_field(payload, "body")) or "",
        value=value,
    )
    return NormalizedAnswerItemPayload(
        raw=payload,
        evidence_state=_evidence_state_from_value(
            _field(payload, "evidence_state", "evidenceState")
        ),
        label=label,
        body=body,
        value=value,
        source_unit_id=_optional_string(
            _field(payload, "source_unit_id", "sourceUnitId")
        ),
        evidence_snippet=_optional_string(
            _field(payload, "evidence_snippet", "evidenceSnippet")
        ),
    )


def _item_id(*, payload: dict[object, object], index: int) -> str:
    value = _optional_string(_field(payload, "id"))
    if value is None:
        return f"answer_{index}"
    if value.startswith("su_"):
        return f"answer_{index}"
    normalized = "".join(
        char if char.isalnum() or char == "_" else "_" for char in value.strip().lower()
    )
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized or f"answer_{index}"


def _display_label(*, raw_label: str | None, value: str | None) -> str:
    if raw_label is None:
        return "답변"
    normalized_label = " ".join(raw_label.split())
    normalized_value = " ".join((value or "").split())
    if normalized_value and normalized_label == normalized_value:
        return "답변"
    if normalized_label.startswith("su_"):
        return "답변"
    return normalized_label or "답변"


def _display_body(*, question: str, label: str, body: str, value: str | None) -> str:
    normalized_body = " ".join(body.split())
    normalized_value = " ".join((value or "").split())
    if normalized_value and normalized_body == normalized_value:
        subject = _question_subject(question)
        if subject:
            return f"{subject}: {normalized_value}"
        if label != "답변":
            return f"{label}: {normalized_value}"
        return f"자료에서 확인한 내용은 {normalized_value}입니다."
    return normalized_body


def _question_subject(question: str) -> str | None:
    stripped = question.strip().rstrip("?!.。")
    for suffix in (
        "가 어떻게 돼",
        "이 어떻게 돼",
        "은 어떻게 돼",
        "는 어떻게 돼",
        " 어떻게 돼",
        "가 뭐야",
        "이 뭐야",
        "은 뭐야",
        "는 뭐야",
        " 뭐야",
    ):
        if stripped.endswith(suffix):
            subject = stripped[: -len(suffix)].strip()
            return subject or None
    return None


def _evidence_state_from_value(value: object) -> EvidenceState:
    if not isinstance(value, str):
        return EvidenceState.MISSING
    try:
        return EvidenceState(value.strip().lower())
    except ValueError:
        return EvidenceState.MISSING


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
