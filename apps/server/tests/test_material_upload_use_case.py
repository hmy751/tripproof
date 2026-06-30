from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from server.materials.layout import PageLayout, PdfLine, PdfWord
from server.materials.observation import InMemoryMaterialUploadObservationSink
from server.materials.pdf import ParsedPdf
from server.materials.store import MaterialStore
import server.use_cases.materials as materials_use_case
from server.runtime.config_snapshot import RuntimeConfigSettings
from server.testing import InMemoryRetrievalRepository
from server.use_cases.materials import (
    MaterialUploadTooLargeError,
    UploadMaterialCommand,
    UploadMaterialUseCase,
)


def test_upload_material_use_case_returns_ready_trace_without_http_adapter() -> None:
    sink = InMemoryMaterialUploadObservationSink()
    store = MaterialStore(
        retrieval_repository=InMemoryRetrievalRepository(), retrieval_backend="memory"
    )
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


def test_upload_material_use_case_builds_layout_source_units(monkeypatch) -> None:
    sink = InMemoryMaterialUploadObservationSink()
    store = MaterialStore(
        retrieval_repository=InMemoryRetrievalRepository(), retrieval_backend="memory"
    )
    use_case = UploadMaterialUseCase(
        store=store,
        observation_sink=sink,
        runtime_config=_runtime_config(store),
        max_upload_bytes=20 * 1024 * 1024,
    )
    layout = _page_layout(
        [
            _layout_line("Booking Details", top=72, size=16),
            _layout_line("Arrival : 2025-03-09", top=100),
            _layout_line("Departure : 2025-03-13", top=120),
            _layout_line("Bring a valid photo ID at check-in.", top=150),
        ]
    )
    monkeypatch.setattr(
        materials_use_case,
        "parse_pdf",
        lambda _raw: ParsedPdf(
            page_count=1,
            text=(
                "[page 1]\nBooking Details\nArrival : 2025-03-09\n"
                "Departure : 2025-03-13\nBring a valid photo ID at check-in."
            ),
            preview="Booking Details Arrival : 2025-03-09",
            layout_pages=(layout,),
        ),
    )

    result = use_case.run(
        UploadMaterialCommand(
            file_name="booking.pdf",
            content_type="application/pdf",
            uploaded_bytes=b"%PDF layout bytes",
            display_name="Booking",
        )
    )

    records = store.retrieval_records([result.material.id])

    assert result.material.status == "ready"
    assert len(records.source_units) >= 3
    assert records.source_units[0].metadata["extraction_backend"] == "pdfplumber"
    assert any(
        unit.metadata["structural_kind"] == "key_value_row"
        for unit in records.source_units
    )
    assert not hasattr(result.material, "debug")
    assert not hasattr(result.material, "raw")


def test_upload_material_use_case_records_too_large_failure_without_http_adapter() -> (
    None
):
    sink = InMemoryMaterialUploadObservationSink()
    store = MaterialStore(
        retrieval_repository=InMemoryRetrievalRepository(), retrieval_backend="memory"
    )
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
    return _pdf_with_positioned_lines([(24, 72, 720, text)])


def _pdf_with_positioned_lines(lines: list[tuple[int, int, int, str]]) -> bytes:
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
    commands = [
        f"BT /F1 {font_size} Tf {x} {y} Td ({_pdf_literal(text)}) Tj ET"
        for font_size, x, y, text in lines
    ]
    stream.set_data("\n".join(commands).encode("utf-8"))
    page[NameObject("/Contents")] = stream
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_layout(lines: list[PdfLine]) -> PageLayout:
    return PageLayout(page=1, width=612, height=792, lines=tuple(lines))


def _layout_line(text: str, *, top: float, size: float = 10) -> PdfLine:
    words = []
    for index, part in enumerate(text.split(), start=1):
        x0 = 72 + (index - 1) * 52
        words.append(
            PdfWord(
                page=1,
                text=part,
                x0=x0,
                top=top,
                x1=x0 + max(10, len(part) * 5),
                bottom=top + size,
                order=index,
                font_name="Helvetica",
                size=size,
            )
        )
    return PdfLine(
        page=1,
        text=text,
        words=tuple(words),
        x0=min(word.x0 for word in words),
        top=top,
        x1=max(word.x1 for word in words),
        bottom=top + size,
        order=1,
        font_size=size,
    )


def _runtime_config(store: MaterialStore) -> RuntimeConfigSettings:
    return RuntimeConfigSettings(
        retrieval_backend=store.retrieval_backend,
        retrieval_top_k=3,
        retrieval_similarity_threshold=0.0,
        embedding_auto_generate=store.embedding_auto_generate,
        embedding_profile=store.embedding_profile,
    )
