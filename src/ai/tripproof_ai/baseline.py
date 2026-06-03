from __future__ import annotations

import re

from .models import CandidateEnvelope, RawTripFactCandidate


def extract_candidates(envelope: CandidateEnvelope) -> list[RawTripFactCandidate]:
    candidates: list[RawTripFactCandidate] = []

    for artifact in envelope.artifacts:
        text = envelope.material_texts.get(artifact.id, "")
        if not text:
            continue

        checkin = re.search(r"체크인\s*(\d{1,2}:\d{2})", text)
        if checkin:
            candidates.append(
                RawTripFactCandidate(
                    id="checkin-start",
                    artifact_id=artifact.id,
                    schedule="숙소 체크인",
                    label="체크인 시작 시간",
                    value=checkin.group(1),
                    confidence=0.94,
                    locator="예약 요약 영역",
                    snippet=_snippet(text, checkin.start()),
                )
            )

        late_arrival = re.search(r"(\d{1,2}:\d{2})\s*이후.+?(연락|메시지)", text)
        if late_arrival:
            candidates.append(
                RawTripFactCandidate(
                    id="late-arrival",
                    artifact_id=artifact.id,
                    schedule="숙소 체크인",
                    label="늦은 도착 조건",
                    value=f"{late_arrival.group(1)} 이후 도착 시 연락 필요",
                    confidence=0.72,
                    locator="도착 지연 안내",
                    snippet=_snippet(text, late_arrival.start()),
                    sensitive=False,
                )
            )

        if "출입 코드" in text or "출입코드" in text:
            candidates.append(
                RawTripFactCandidate(
                    id="door-code",
                    artifact_id=artifact.id,
                    schedule="숙소 체크인",
                    label="출입 코드",
                    value=None,
                    confidence=0.48,
                    locator="셀프 체크인 안내",
                    snippet=_snippet(text, text.find("출입")),
                    sensitive=True,
                )
            )

    return candidates


def _snippet(text: str, start: int, width: int = 80) -> str:
    start = max(start, 0)
    end = min(len(text), start + width)
    return text[start:end].strip()
