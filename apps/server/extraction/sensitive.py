from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Iterable

from server.retrieval.models import SourceUnit


class SensitiveKind(StrEnum):
    BOOKING_ID = "booking_id"
    BOOKING_REFERENCE = "booking_reference"
    GUEST_NAME = "guest_name"
    MEMBER_ID = "member_id"
    PAYMENT_CARD = "payment_card"
    PROPERTY_CONTACT = "property_contact"
    EXACT_ADDRESS = "exact_address"


@dataclass(frozen=True)
class SensitiveFinding:
    kind: SensitiveKind
    source_unit_id: str
    locator: str


_SENSITIVE_RULES: tuple[tuple[SensitiveKind, tuple[tuple[str, ...], ...], tuple[str, ...]], ...] = (
    (SensitiveKind.BOOKING_ID, (("booking", "id"),), ("예약번호",)),
    (SensitiveKind.BOOKING_REFERENCE, (("booking", "reference"),), ("예약참조",)),
    (SensitiveKind.GUEST_NAME, (("client",), ("guest",)), ("고객명", "투숙객")),
    (SensitiveKind.MEMBER_ID, (("member", "id"),), ("회원id",)),
    (SensitiveKind.PAYMENT_CARD, (("mastercard",), ("visa",), ("card",)), ("신용카드", "카드번호")),
    (SensitiveKind.PROPERTY_CONTACT, (("contact",), ("phone",)), ("연락처",)),
    (SensitiveKind.EXACT_ADDRESS, (("address",),), ("주소",)),
)


def detect_sensitive_findings(source_units: Iterable[SourceUnit]) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    seen: set[tuple[SensitiveKind, str]] = set()

    for unit in source_units:
        normalized = _normalize_text(unit.text)
        tokens = _ascii_word_tokens(unit.text)
        for kind, token_sequences, compact_phrases in _SENSITIVE_RULES:
            if not _contains_sensitive_marker(
                normalized=normalized,
                tokens=tokens,
                token_sequences=token_sequences,
                compact_phrases=compact_phrases,
            ):
                continue
            key = (kind, unit.id)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                SensitiveFinding(
                    kind=kind,
                    source_unit_id=unit.id,
                    locator=unit.locator,
                )
            )

    return findings


def _contains_sensitive_marker(
    *,
    normalized: str,
    tokens: list[str],
    token_sequences: tuple[tuple[str, ...], ...],
    compact_phrases: tuple[str, ...],
) -> bool:
    return any(phrase in normalized for phrase in compact_phrases) or any(
        _contains_token_sequence(tokens=tokens, sequence=sequence) for sequence in token_sequences
    )


def _normalize_text(value: str) -> str:
    return "".join(value.lower().split())


def _ascii_word_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in value.lower():
        if char.isascii() and char.isalnum():
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _contains_token_sequence(*, tokens: list[str], sequence: tuple[str, ...]) -> bool:
    if not sequence or len(sequence) > len(tokens):
        return False
    return any(tokens[index : index + len(sequence)] == list(sequence) for index in range(len(tokens)))
