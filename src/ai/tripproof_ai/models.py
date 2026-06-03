from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ArtifactKind = Literal["image", "pdf", "message", "receipt", "unknown"]


@dataclass(frozen=True)
class Artifact:
    id: str
    name: str
    file_name: str
    kind: ArtifactKind

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Artifact":
        return cls(
            id=str(value["id"]),
            name=str(value["name"]),
            file_name=str(value["fileName"]),
            kind=_artifact_kind(value.get("kind", "unknown")),
        )


@dataclass(frozen=True)
class CandidateEnvelope:
    artifacts: list[Artifact]
    material_texts: dict[str, str]
    user_question: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CandidateEnvelope":
        return cls(
            artifacts=[Artifact.from_dict(item) for item in value.get("artifacts", [])],
            material_texts={
                str(key): str(text) for key, text in value.get("materialTexts", {}).items()
            },
            user_question=value.get("userQuestion"),
        )


@dataclass(frozen=True)
class RawTripFactCandidate:
    id: str
    schedule: str
    label: str
    value: str | None
    confidence: float
    artifact_id: str | None = None
    locator: str | None = None
    snippet: str | None = None
    sensitive: bool = False
    conflict_with: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "schedule": self.schedule,
            "label": self.label,
            "value": self.value,
            "confidence": self.confidence,
            "sensitive": self.sensitive,
        }
        if self.artifact_id is not None:
            result["artifactId"] = self.artifact_id
        if self.locator is not None:
            result["locator"] = self.locator
        if self.snippet is not None:
            result["snippet"] = self.snippet
        if self.conflict_with:
            result["conflictWith"] = self.conflict_with
        return result


def _artifact_kind(value: Any) -> ArtifactKind:
    if value in {"image", "pdf", "message", "receipt", "unknown"}:
        return value
    return "unknown"
