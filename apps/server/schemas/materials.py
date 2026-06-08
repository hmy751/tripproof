from __future__ import annotations

from typing import Literal

from pydantic import Field

from server.schemas.base import ApiModel

MaterialStatus = Literal["ready", "failed"]


class Material(ApiModel):
    id: str
    name: str
    file_name: str = Field(alias="fileName")
    content_type: str | None = Field(default=None, alias="contentType")
    status: MaterialStatus
    page_count: int | None = Field(default=None, alias="pageCount")
    preview: str | None = None
    error: str | None = None
