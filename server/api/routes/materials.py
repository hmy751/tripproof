from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.api.deps import get_material_store
from server.core.config import MAX_UPLOAD_BYTES
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
    file: UploadFile = File(...),
    display_name: str | None = Form(default=None, alias="displayName"),
) -> Material:
    file_name = file.filename or "uploaded.pdf"
    material_name = _material_name(display_name, file_name)
    content_type = file.content_type
    raw = await file.read()

    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF 파일이 너무 큽니다.")

    if not _looks_like_pdf(file_name, content_type):
        return store.add_failed(
            name=material_name,
            file_name=file_name,
            content_type=content_type,
            error="PDF 파일만 지원합니다.",
        )

    try:
        parsed = parse_pdf(raw)
    except PdfParseError as error:
        return store.add_failed(
            name=material_name,
            file_name=file_name,
            content_type=content_type,
            error=str(error),
        )

    return store.add_ready(
        name=material_name,
        file_name=file_name,
        content_type=content_type,
        page_count=parsed.page_count,
        text=parsed.text,
        preview=parsed.preview,
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
