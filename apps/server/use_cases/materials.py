from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.materials.observation import (
    MaterialUploadFailureKind,
    MaterialUploadObservationReporter,
    MaterialUploadObservationSink,
)
from server.materials.pdf import PdfParseError, parse_pdf
from server.materials.store import MaterialStore
from server.runtime.config_snapshot import RuntimeConfigSettings, runtime_config_snapshot_from_settings
from server.schemas.materials import Material, MaterialStatus


@dataclass(frozen=True)
class UploadMaterialCommand:
    file_name: str
    content_type: str | None
    uploaded_bytes: bytes
    display_name: str | None


@dataclass(frozen=True)
class UploadMaterialTrace:
    file_name: str
    material_name: str
    content_type: str | None
    size_bytes: int
    size_limit_bytes: int
    final_status: MaterialStatus
    material_id: str | None = None
    failure_kind: MaterialUploadFailureKind | None = None
    parsed_page_count: int | None = None


@dataclass(frozen=True)
class UploadMaterialResult:
    material: Material
    trace: UploadMaterialTrace


class MaterialUploadTooLargeError(ValueError):
    def __init__(self, trace: UploadMaterialTrace) -> None:
        super().__init__("PDF file is too large.")
        self.trace = trace


class UploadMaterialUseCase:
    def __init__(
        self,
        *,
        store: MaterialStore,
        observation_sink: MaterialUploadObservationSink,
        runtime_config: RuntimeConfigSettings,
        max_upload_bytes: int,
    ) -> None:
        self._store = store
        self._observation_sink = observation_sink
        self._runtime_config = runtime_config
        self._max_upload_bytes = max_upload_bytes

    def run(self, command: UploadMaterialCommand) -> UploadMaterialResult:
        material_name = _material_name(command.display_name, command.file_name)
        observation = MaterialUploadObservationReporter(
            sink=self._observation_sink,
            file_name=command.file_name,
            content_type=command.content_type,
            size_bytes=len(command.uploaded_bytes),
            size_limit_bytes=self._max_upload_bytes,
            runtime_config_snapshot=runtime_config_snapshot_from_settings(self._runtime_config),
        )

        if len(command.uploaded_bytes) > self._max_upload_bytes:
            trace = UploadMaterialTrace(
                file_name=command.file_name,
                material_name=material_name,
                content_type=command.content_type,
                size_bytes=len(command.uploaded_bytes),
                size_limit_bytes=self._max_upload_bytes,
                final_status="failed",
                failure_kind="size_limit_exceeded",
            )
            observation.upload_too_large()
            observation.emit()
            raise MaterialUploadTooLargeError(trace)

        if not _looks_like_pdf(command.file_name, command.content_type):
            material = self._store.add_failed(
                name=material_name,
                file_name=command.file_name,
                content_type=command.content_type,
                error="PDF 파일만 지원합니다.",
            )
            observation.unsupported_file(material_id=material.id)
            observation.emit()
            return UploadMaterialResult(
                material=material,
                trace=UploadMaterialTrace(
                    file_name=command.file_name,
                    material_name=material_name,
                    content_type=command.content_type,
                    size_bytes=len(command.uploaded_bytes),
                    size_limit_bytes=self._max_upload_bytes,
                    final_status="failed",
                    material_id=material.id,
                    failure_kind="unsupported_file",
                ),
            )

        try:
            parsed_pdf = parse_pdf(command.uploaded_bytes)
        except PdfParseError as error:
            material = self._store.add_failed(
                name=material_name,
                file_name=command.file_name,
                content_type=command.content_type,
                error=str(error),
            )
            observation.pdf_parse_failed(material_id=material.id)
            observation.emit()
            return UploadMaterialResult(
                material=material,
                trace=UploadMaterialTrace(
                    file_name=command.file_name,
                    material_name=material_name,
                    content_type=command.content_type,
                    size_bytes=len(command.uploaded_bytes),
                    size_limit_bytes=self._max_upload_bytes,
                    final_status="failed",
                    material_id=material.id,
                    failure_kind="parse_failed",
                ),
            )

        observation.pdf_parsed(page_count=parsed_pdf.page_count)

        try:
            material = self._store.add_ready(
                name=material_name,
                file_name=command.file_name,
                content_type=command.content_type,
                page_count=parsed_pdf.page_count,
                text=parsed_pdf.text,
                preview=parsed_pdf.preview,
                observation=observation.recorder_for_material_store(),
            )
        except Exception:
            observation.emit()
            raise

        observation.emit()
        return UploadMaterialResult(
            material=material,
            trace=UploadMaterialTrace(
                file_name=command.file_name,
                material_name=material_name,
                content_type=command.content_type,
                size_bytes=len(command.uploaded_bytes),
                size_limit_bytes=self._max_upload_bytes,
                final_status="ready",
                material_id=material.id,
                parsed_page_count=parsed_pdf.page_count,
            ),
        )


def _looks_like_pdf(file_name: str, content_type: str | None) -> bool:
    if content_type == "application/pdf":
        return True
    return file_name.lower().endswith(".pdf")


def _material_name(display_name: str | None, file_name: str) -> str:
    trimmed = (display_name or "").strip()
    if trimmed:
        return trimmed

    stem = Path(file_name).stem.strip()
    return stem or "PDF 자료"
