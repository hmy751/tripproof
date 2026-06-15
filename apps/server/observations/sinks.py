from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from server.materials.observation import MaterialUploadObservationRecord
from server.observations.envelope import ObservationExportEnvelope
from server.observations.serializers import (
    material_upload_observation_export,
    observation_export_to_dict,
    question_observation_export,
)
from server.questions.observation import QuestionObservationRecord


class ObservationExporter(Protocol):
    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        raise NotImplementedError


class NoopObservationExporter:
    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        return None


class FanoutObservationExporter:
    def __init__(self, exporters: list[ObservationExporter]) -> None:
        self._exporters = list(exporters)

    @property
    def exporters(self) -> list[ObservationExporter]:
        return list(self._exporters)

    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        for exporter in self._exporters:
            try:
                exporter.export_observation(envelope)
            except Exception:
                continue


class LocalArtifactObservationExporter:
    def __init__(
        self,
        directory: str | Path,
        *,
        file_name: str = "observation-export.jsonl",
    ) -> None:
        self._path = Path(directory) / file_name

    @property
    def path(self) -> Path:
        return self._path

    def export_observation(self, envelope: ObservationExportEnvelope) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            observation_export_to_dict(envelope),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._path.open("a", encoding="utf-8") as export_file:
            export_file.write(f"{line}\n")


class MaterialUploadObservationExportSink:
    def __init__(self, exporter: ObservationExporter) -> None:
        self._exporter = exporter

    def record_material_upload(self, record: MaterialUploadObservationRecord) -> None:
        self._exporter.export_observation(material_upload_observation_export(record))


class QuestionObservationExportSink:
    def __init__(self, exporter: ObservationExporter) -> None:
        self._exporter = exporter

    def record_question_answer(self, record: QuestionObservationRecord) -> None:
        self._exporter.export_observation(question_observation_export(record))


def create_observation_exporter_from_directory(
    directory: str | Path | None,
) -> ObservationExporter:
    if directory is None or str(directory).strip() == "":
        return NoopObservationExporter()
    return LocalArtifactObservationExporter(directory)
