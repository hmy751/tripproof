from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .ingest.pdf import PdfParseError, parse_pdf
from .models import Material, QuestionRequest, QuestionResponse
from .storage.memory import MaterialStore, StoredMaterial

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def create_app(store: MaterialStore | None = None) -> FastAPI:
    app = FastAPI(title="TripProof Backend")
    app.state.material_store = store or MaterialStore()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/materials", response_model=list[Material])
    def list_materials() -> list[Material]:
        return app.state.material_store.list_public()

    @app.post("/api/materials", response_model=Material)
    async def upload_material(
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
            return app.state.material_store.add_failed(
                name=material_name,
                file_name=file_name,
                content_type=content_type,
                error="PDF 파일만 지원합니다.",
            )

        try:
            parsed = parse_pdf(raw)
        except PdfParseError as error:
            return app.state.material_store.add_failed(
                name=material_name,
                file_name=file_name,
                content_type=content_type,
                error=str(error),
            )

        return app.state.material_store.add_ready(
            name=material_name,
            file_name=file_name,
            content_type=content_type,
            page_count=parsed.page_count,
            text=parsed.text,
            preview=parsed.preview,
        )

    @app.post("/api/questions", response_model=QuestionResponse)
    def ask_question(payload: QuestionRequest) -> QuestionResponse:
        question = payload.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="질문을 입력해야 합니다.")

        ready_materials = app.state.material_store.ready_materials(payload.material_ids)
        if not ready_materials:
            return QuestionResponse(
                status="blocked",
                message="읽기 완료된 자료가 없어 답할 수 없습니다.",
                material_ids=[],
                material_count=0,
                page_count=0,
                char_count=0,
                excerpt=None,
            )

        page_count = sum(material.page_count for material in ready_materials)
        char_count = sum(len(material.text) for material in ready_materials)
        excerpt = _select_excerpt(ready_materials, question)

        return QuestionResponse(
            status="accepted",
            message=f"읽기 완료 자료 {len(ready_materials)}개를 기준으로 질문을 받았습니다.",
            material_ids=[material.id for material in ready_materials],
            material_count=len(ready_materials),
            page_count=page_count,
            char_count=char_count,
            excerpt=excerpt,
        )

    return app


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


def _select_excerpt(materials: list[StoredMaterial], question: str) -> str | None:
    combined = "\n\n".join(material.text for material in materials)
    normalized = re.sub(r"\s+", " ", combined).strip()
    if not normalized:
        return None

    lower_text = normalized.lower()
    terms = [term.lower() for term in re.findall(r"[\w가-힣]+", question) if len(term) >= 2]

    start = 0
    for term in terms:
        index = lower_text.find(term)
        if index >= 0:
            start = max(index - 80, 0)
            break

    excerpt = normalized[start : start + 420].strip()
    return excerpt or None


app = create_app()
