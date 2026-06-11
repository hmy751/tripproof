from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.api.deps import get_material_store, get_material_upload_observation_sink
from server.core.config import MAX_UPLOAD_BYTES
from server.materials.observation import (
    MaterialUploadObservationRecorder,
    MaterialUploadObservationSink,
    emit_material_upload_observation,
)
from server.materials.pdf import PdfParseError, parse_pdf
from server.materials.store import MaterialStore
from server.schemas.materials import Material

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=list[Material])
def list_materials(store: Annotated[MaterialStore, Depends(get_material_store)]) -> list[Material]:
    return store.list_public()


@router.post("", response_model=Material)
async def upload_material(
    store: Annotated[MaterialStore, Depends(get_material_store)],
    observation_sink: Annotated[MaterialUploadObservationSink, Depends(get_material_upload_observation_sink)],
    file: UploadFile = File(...),
    display_name: str | None = Form(default=None, alias="displayName"),
) -> Material:
    file_name = file.filename or "uploaded.pdf"
    material_name = _material_name(display_name, file_name)
    content_type = file.content_type
    raw = await file.read()
    observation = MaterialUploadObservationRecorder(
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(raw),
        size_limit_bytes=MAX_UPLOAD_BYTES,
    )

    if len(raw) > MAX_UPLOAD_BYTES:
        observation.fail("upload_snapshot", "size_limit_exceeded")
        observation.finalize("failed", failure_kind="size_limit_exceeded")
        emit_material_upload_observation(sink=observation_sink, recorder=observation)
        raise HTTPException(status_code=413, detail="PDF 파일이 너무 큽니다.")

    if not _looks_like_pdf(file_name, content_type):
        observation.fail("upload_snapshot", "unsupported_file")
        material = store.add_failed(
            name=material_name,
            file_name=file_name,
            content_type=content_type,
            error="PDF 파일만 지원합니다.",
        )
        observation.finalize("failed", material_id=material.id, failure_kind="unsupported_file")
        emit_material_upload_observation(sink=observation_sink, recorder=observation)
        return material

    try:
        parsed = parse_pdf(raw)
    except PdfParseError as error:
        observation.fail("pdf_parse", "parse_failed")
        material = store.add_failed(
            name=material_name,
            file_name=file_name,
            content_type=content_type,
            error=str(error),
        )
        observation.finalize("failed", material_id=material.id, failure_kind="parse_failed")
        emit_material_upload_observation(sink=observation_sink, recorder=observation)
        return material

    observation.succeed("pdf_parse", facts={"page_count": parsed.page_count})

    try:
        material = store.add_ready(
            name=material_name,
            file_name=file_name,
            content_type=content_type,
            page_count=parsed.page_count,
            text=parsed.text,
            preview=parsed.preview,
            observation=observation,
        )
    except Exception:
        emit_material_upload_observation(sink=observation_sink, recorder=observation)
        raise

    emit_material_upload_observation(sink=observation_sink, recorder=observation)
    return material


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
