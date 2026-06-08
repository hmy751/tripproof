from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from server.api.deps import get_material_store
from server.materials.store import MaterialStore
from server.retrieval.search import select_excerpt
from server.schemas.questions import QuestionRequest, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionResponse)
def ask_question(
    payload: QuestionRequest,
    store: Annotated[MaterialStore, Depends(get_material_store)],
) -> QuestionResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="질문을 입력해야 합니다.")

    ready_materials = store.ready_materials(payload.material_ids)
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
    excerpt = select_excerpt([material.text for material in ready_materials], question)

    return QuestionResponse(
        status="accepted",
        message=f"읽기 완료 자료 {len(ready_materials)}개를 기준으로 질문을 받았습니다.",
        material_ids=[material.id for material in ready_materials],
        material_count=len(ready_materials),
        page_count=page_count,
        char_count=char_count,
        excerpt=excerpt,
    )
