from __future__ import annotations

from typing import Literal

from pydantic import Field

from server.schemas.base import ApiModel

QuestionStatus = Literal["accepted", "blocked"]


class QuestionRequest(ApiModel):
    question: str
    material_ids: list[str] | None = Field(default=None, alias="materialIds")


class QuestionResponse(ApiModel):
    status: QuestionStatus
    message: str
    material_ids: list[str] = Field(alias="materialIds")
    material_count: int = Field(alias="materialCount")
    page_count: int = Field(alias="pageCount")
    char_count: int = Field(alias="charCount")
    excerpt: str | None = None
    excerpt_locator: str | None = Field(default=None, alias="excerptLocator")
    excerpt_source_unit_id: str | None = Field(default=None, alias="excerptSourceUnitId")
