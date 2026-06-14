from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from server.materials.observation import InMemoryMaterialUploadObservationSink
from server.materials.store import MaterialStore
from server.runtime.config_snapshot import RuntimeConfigSettings
from server.use_cases.materials import (
    MaterialUploadTooLargeError,
    UploadMaterialCommand,
    UploadMaterialUseCase,
)


def test_upload_material_use_case_returns_ready_trace_without_http_adapter() -> None:
    sink = InMemoryMaterialUploadObservationSink()
    store = MaterialStore(retrieval_backend="memory")
    use_case = UploadMaterialUseCase(
        store=store,
        observation_sink=sink,
        runtime_config=_runtime_config(store),
        max_upload_bytes=20 * 1024 * 1024,
    )

    result = use_case.run(
        UploadMaterialCommand(
            file_name="booking.pdf",
            content_type="application/pdf",
            uploaded_bytes=_pdf_with_text("Check-in starts at 15:00."),
            display_name="Agoda Fukuoka",
        )
    )

    assert result.material.status == "ready"
    assert result.material.name == "Agoda Fukuoka"
    assert result.trace.file_name == "booking.pdf"
    assert result.trace.material_name == "Agoda Fukuoka"
    assert result.trace.final_status == "ready"
    assert result.trace.material_id == result.material.id
    assert result.trace.failure_kind is None
    assert result.trace.parsed_page_count == 1

    record = sink.records[0]
    assert record.material_id == result.material.id
    assert record.step("pdf_parse").status == "succeeded"
    assert record.step("retrieval_preparation").status == "succeeded"
    assert record.final_material_status == "ready"
    assert record.failure_kind is None


def test_upload_material_use_case_records_too_large_failure_without_http_adapter() -> None:
    sink = InMemoryMaterialUploadObservationSink()
    store = MaterialStore(retrieval_backend="memory")
    use_case = UploadMaterialUseCase(
        store=store,
        observation_sink=sink,
        runtime_config=_runtime_config(store),
        max_upload_bytes=5,
    )

    with pytest.raises(MaterialUploadTooLargeError) as exc_info:
        use_case.run(
            UploadMaterialCommand(
                file_name="booking.pdf",
                content_type="application/pdf",
                uploaded_bytes=b"%PDF-too-large",
                display_name=None,
            )
        )

    assert exc_info.value.trace.final_status == "failed"
    assert exc_info.value.trace.failure_kind == "size_limit_exceeded"
    record = sink.records[0]
    assert record.material_id is None
    assert record.step("upload_snapshot").status == "failed"
    assert record.step("upload_snapshot").failure_kind == "size_limit_exceeded"
    assert record.step("content_extraction").status == "not_started"
    assert record.final_material_status == "failed"
    assert record.failure_kind == "size_limit_exceeded"


def _pdf_with_text(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("utf-8"))
    page[NameObject("/Contents")] = stream
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _runtime_config(store: MaterialStore) -> RuntimeConfigSettings:
    return RuntimeConfigSettings(
        retrieval_backend=store.retrieval_backend,
        retrieval_top_k=3,
        retrieval_similarity_threshold=0.0,
        embedding_auto_generate=store.embedding_auto_generate,
        embedding_profile=store.embedding_profile,
    )
