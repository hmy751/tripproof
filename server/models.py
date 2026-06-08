from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MaterialStatus = Literal["ready", "failed"]
QuestionStatus = Literal["accepted", "blocked"]


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Material(ApiModel):
    id: str
    name: str
    file_name: str = Field(alias="fileName")
    content_type: str | None = Field(default=None, alias="contentType")
    status: MaterialStatus
    page_count: int | None = Field(default=None, alias="pageCount")
    preview: str | None = None
    error: str | None = None


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
