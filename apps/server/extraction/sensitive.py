from __future__ import annotations

import re
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


_SENSITIVE_PATTERNS: tuple[tuple[SensitiveKind, re.Pattern[str]], ...] = (
    (SensitiveKind.BOOKING_ID, re.compile(r"\bbooking\s*id\b|예약\s*번호", re.IGNORECASE)),
    (SensitiveKind.BOOKING_REFERENCE, re.compile(r"\bbooking\s*reference\b|예약\s*참조", re.IGNORECASE)),
    (SensitiveKind.GUEST_NAME, re.compile(r"\b(client|guest)\b|고객명|투숙객", re.IGNORECASE)),
    (SensitiveKind.MEMBER_ID, re.compile(r"\bmember\s*id\b|회원\s*id", re.IGNORECASE)),
    (SensitiveKind.PAYMENT_CARD, re.compile(r"\b(mastercard|visa|card)\b|신용\s*카드|카드\s*번호", re.IGNORECASE)),
    (SensitiveKind.PROPERTY_CONTACT, re.compile(r"\b(contact|phone)\b|연락처", re.IGNORECASE)),
    (SensitiveKind.EXACT_ADDRESS, re.compile(r"\baddress\b|주소", re.IGNORECASE)),
)


def detect_sensitive_findings(source_units: Iterable[SourceUnit]) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    seen: set[tuple[SensitiveKind, str]] = set()

    for unit in source_units:
        for kind, pattern in _SENSITIVE_PATTERNS:
            if not pattern.search(unit.text):
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
