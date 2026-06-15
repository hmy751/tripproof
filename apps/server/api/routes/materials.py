from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.api.deps import (
    get_material_store,
    get_material_upload_observation_sink,
    get_runtime_config_settings,
)
from server.core.config import MAX_UPLOAD_BYTES
from server.materials.observation import MaterialUploadObservationSink
from server.materials.store import MaterialStore
from server.runtime.config_snapshot import RuntimeConfigSettings
from server.schemas.materials import Material
from server.use_cases.materials import (
    MaterialUploadTooLargeError,
    UploadMaterialCommand,
    UploadMaterialUseCase,
)

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.get("", response_model=list[Material])
def list_materials(
    store: Annotated[MaterialStore, Depends(get_material_store)],
) -> list[Material]:
    return store.list_public()


@router.post("", response_model=Material)
async def upload_material(
    store: Annotated[MaterialStore, Depends(get_material_store)],
    observation_sink: Annotated[
        MaterialUploadObservationSink, Depends(get_material_upload_observation_sink)
    ],
    runtime_config: Annotated[
        RuntimeConfigSettings, Depends(get_runtime_config_settings)
    ],
    file: UploadFile = File(...),
    display_name: str | None = Form(default=None, alias="displayName"),
) -> Material:
    file_name = file.filename or "uploaded.pdf"
    use_case = UploadMaterialUseCase(
        store=store,
        observation_sink=observation_sink,
        runtime_config=runtime_config,
        max_upload_bytes=MAX_UPLOAD_BYTES,
    )
    try:
        result = use_case.run(
            UploadMaterialCommand(
                file_name=file_name,
                content_type=file.content_type,
                uploaded_bytes=await file.read(),
                display_name=display_name,
            )
        )
    except MaterialUploadTooLargeError as error:
        raise HTTPException(
            status_code=413, detail="PDF 파일이 너무 큽니다."
        ) from error
    return result.material
