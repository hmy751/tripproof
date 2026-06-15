from __future__ import annotations

from pydantic import Field

from server.schemas.base import ApiModel
from server.schemas.answers import ChatAnswerResponse
from server.questions.models import QuestionAnswerResult, QuestionStatus


class QuestionRequest(ApiModel):
    question: str
    material_ids: list[str] | None = Field(default=None, alias="materialIds")


class QuestionResponse(ApiModel):
    status: QuestionStatus
    message: str
    answer: ChatAnswerResponse
    material_ids: list[str] = Field(alias="materialIds")
    material_count: int = Field(alias="materialCount")
    page_count: int = Field(alias="pageCount")
    char_count: int = Field(alias="charCount")

    @classmethod
    def from_domain(cls, result: QuestionAnswerResult) -> "QuestionResponse":
        return cls(
            status=result.status,
            message=result.message,
            answer=ChatAnswerResponse.from_domain(result.answer),
            material_ids=result.material_ids,
            material_count=result.material_count,
            page_count=result.page_count,
            char_count=result.char_count,
        )
