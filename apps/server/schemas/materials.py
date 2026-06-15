from __future__ import annotations

from pydantic import Field

from server.materials.models import MaterialStatus, PublicMaterial
from server.schemas.base import ApiModel


class Material(ApiModel):
    id: str
    name: str
    file_name: str = Field(alias="fileName")
    content_type: str | None = Field(default=None, alias="contentType")
    status: MaterialStatus
    page_count: int | None = Field(default=None, alias="pageCount")
    preview: str | None = None
    error: str | None = None

    @classmethod
    def from_domain(cls, material: PublicMaterial) -> "Material":
        return cls(
            id=material.id,
            name=material.name,
            file_name=material.file_name,
            content_type=material.content_type,
            status=material.status,
            page_count=material.page_count,
            preview=material.preview,
            error=material.error,
        )
