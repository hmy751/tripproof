from __future__ import annotations

from server.materials.layout import (
    PageLayout,
    PdfLine,
    PdfTableCell,
    PdfTableRow,
    PdfWord,
)
from server.retrieval.chunking import build_source_units


def test_layout_source_units_split_key_value_rows() -> None:
    layout = _page_layout(
        [
            _line("Arrival : 2025-03-09", top=72, words_x=[72, 132, 180]),
            _line("Departure : 2025-03-13", top=92, words_x=[72, 150, 205]),
            _line("Guest : MYEONGYEON HAM", top=112, words_x=[72, 125, 190]),
        ]
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    assert [unit.text for unit in units] == [
        "Arrival : 2025-03-09",
        "Departure : 2025-03-13",
        "Guest : MYEONGYEON HAM",
    ]
    assert [unit.metadata["structural_kind"] for unit in units] == [
        "key_value_row",
        "key_value_row",
        "key_value_row",
    ]
    assert all(unit.metadata["kind"] == "label_value" for unit in units)
    assert all(unit.metadata["fallback_used"] is False for unit in units)


def test_layout_source_units_group_heading_paragraph_and_list_items() -> None:
    layout = _page_layout(
        [
            _line("Important Notice", top=72, size=16),
            _line("Bring a valid photo ID at check-in.", top=94),
            _line("Use the same payment card when requested.", top=112),
            _line("- Breakfast is not included.", top=150, words_x=[82, 118, 172, 202]),
            _line("- Laundry is paid on site.", top=168, words_x=[82, 120, 168, 205]),
        ]
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    assert [unit.metadata["structural_kind"] for unit in units] == [
        "heading_paragraph",
        "list_item",
        "list_item",
    ]
    assert "Important Notice\nBring a valid photo ID" in units[0].text
    assert units[0].metadata["kind"] == "warning"


def test_layout_source_units_split_table_like_rows() -> None:
    layout = _page_layout(
        [
            _line("Room Adults Children", top=72, words_x=[72, 220, 320]),
            _line("Cabin 1 0", top=92, words_x=[72, 220, 320]),
        ]
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    assert [unit.text for unit in units] == [
        "Room Adults Children",
        "Cabin 1 0",
    ]
    assert [unit.metadata["structural_kind"] for unit in units] == [
        "table_row",
        "table_row",
    ]


def test_layout_source_units_add_table_row_field_group() -> None:
    layout = _page_layout(
        [
            _line("Arrival : Departure :", top=72, words_x=[72, 150]),
            _line("2025-03-09 2025-03-13", top=84, words_x=[145, 300]),
            _line("체크인 : 체크아웃 :", top=96, words_x=[72, 220]),
        ],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        "Arrival :\n체크인 :",
                        column_index=1,
                        x0=72,
                        top=70,
                        x1=132,
                        bottom=106,
                    ),
                    _cell(
                        "2025-03-09",
                        column_index=2,
                        x0=140,
                        top=70,
                        x1=210,
                        bottom=106,
                    ),
                    _cell(
                        "Departure :\n체크아웃 :",
                        column_index=3,
                        x0=220,
                        top=70,
                        x1=300,
                        bottom=106,
                    ),
                    _cell(
                        "2025-03-13",
                        column_index=4,
                        x0=310,
                        top=70,
                        x1=380,
                        bottom=106,
                    ),
                ],
            ),
        ),
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    assert units[0].metadata["structural_kind"] == "table_row_group"
    assert units[0].metadata["layout_source"] == "pdfplumber_table_row"
    assert "Arrival" in units[0].text
    assert "체크인" in units[0].text
    assert "Departure" in units[0].text
    assert "체크아웃" in units[0].text
    assert "2025-03-09" in units[0].text
    assert "2025-03-13" in units[0].text


def test_layout_source_units_add_table_cell_field_groups() -> None:
    layout = _page_layout(
        [
            _line("Number of Rooms : 1", top=72),
            _line("객실 수 :", top=84),
            _line("Number of Adults : 1", top=96),
            _line("성인 수 :", top=108),
            _line("Number of Children : 0", top=120),
            _line("아동 수 :", top=132),
            _line("Room Type :", top=144),
            _line("Smart Pod - All Gender", top=156),
        ],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        (
                            "Number of Rooms :\n1\n객실 수 :\n"
                            "Number of Adults :\n1\n성인 수 :\n"
                            "Number of Children :\n0\n아동 수 :\n"
                            "Room Type :\nSmart Pod - All Gender\n객실 타입 :"
                        ),
                        column_index=1,
                        x0=72,
                        top=70,
                        x1=320,
                        bottom=190,
                    ),
                ],
            ),
        ),
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    assert units[0].metadata["structural_kind"] == "field_group"
    assert units[0].metadata["layout_source"] == "pdfplumber_table_cell"
    assert "Number of Rooms" in units[0].text
    assert "Number of Adults" in units[0].text
    assert "Number of Children" in units[0].text
    assert "Room Type" in units[0].text


def test_layout_source_units_add_uncovered_small_section_field_group() -> None:
    layout = _page_layout(
        [
            _line("Arrival : Departure :", top=72, words_x=[72, 220]),
            _line("2025-03-09 2025-03-13", top=84, words_x=[140, 300]),
            _line("Remarks :", top=180),
            _line("NonSmoke,LargeBed", top=194),
            _line("City tax may be paid on site.", top=226),
            _line("Guest list : Example Guest", top=244),
            _line(
                "All special requests are subject to property availability.", top=262
            ),
            _line("Important Notice", top=308, size=16),
            _line("Bring a valid photo ID at check-in.", top=332),
        ],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        "Arrival :\n2025-03-09\nDeparture :\n2025-03-13",
                        column_index=1,
                        x0=72,
                        top=70,
                        x1=320,
                        bottom=112,
                    ),
                ],
            ),
        ),
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    request_group = next(
        unit for unit in units if unit.metadata.get("layout_source") == "line_region"
    )
    assert request_group.metadata["structural_kind"] == "field_group"
    assert request_group.metadata["kind"] == "request_note"
    assert "Remarks" in request_group.text
    assert "NonSmoke,LargeBed" in request_group.text
    assert "special requests" in request_group.text


def test_layout_geometry_drives_boundaries_before_semantic_annotation() -> None:
    first_layout = _page_layout(
        [
            _line("Notes", top=72, size=16),
            _line("Cancellation fee applies after arrival.", top=94),
            _line("City tax may be paid on site.", top=112),
        ]
    )
    second_layout = _page_layout(
        [
            _line("Notes", top=72, size=16),
            _line("Simple welcome message for guests.", top=94),
            _line("Shared lounge opens every morning.", top=112),
        ]
    )

    first_units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(first_layout,),
    )
    second_units = build_source_units(
        material_id="mat_2",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(second_layout,),
    )

    assert [unit.metadata["structural_kind"] for unit in first_units] == [
        unit.metadata["structural_kind"] for unit in second_units
    ]
    assert len(first_units) == len(second_units) == 1
    assert first_units[0].metadata["kind"] != second_units[0].metadata["kind"]


def test_source_units_fall_back_to_text_chunks_without_layout() -> None:
    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nCheck-in starts at 15:00.",
    )

    assert len(units) == 1
    assert units[0].metadata["structural_kind"] == "text_chunk"
    assert units[0].metadata["extraction_backend"] == "pypdf_text"
    assert units[0].metadata["fallback_used"] is True


def _page_layout(
    lines: list[PdfLine],
    *,
    table_rows: tuple[PdfTableRow, ...] = (),
) -> PageLayout:
    return PageLayout(
        page=1,
        width=612,
        height=792,
        lines=tuple(lines),
        table_rows=table_rows,
    )


def _line(
    text: str,
    *,
    top: float,
    words_x: list[float] | None = None,
    size: float = 10,
) -> PdfLine:
    words = []
    x_values = words_x or [72 + index * 48 for index, _part in enumerate(text.split())]
    for index, (part, x0) in enumerate(
        zip(text.split(), x_values, strict=False), start=1
    ):
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


def _table_row(
    *,
    row_index: int,
    cells: list[PdfTableCell],
    table_index: int = 1,
) -> PdfTableRow:
    return PdfTableRow(
        page=1,
        table_index=table_index,
        row_index=row_index,
        cells=tuple(cells),
        x0=min(cell.x0 for cell in cells),
        top=min(cell.top for cell in cells),
        x1=max(cell.x1 for cell in cells),
        bottom=max(cell.bottom for cell in cells),
    )


def _cell(
    text: str,
    *,
    column_index: int,
    x0: float,
    top: float,
    x1: float,
    bottom: float,
    row_index: int = 1,
    table_index: int = 1,
) -> PdfTableCell:
    return PdfTableCell(
        page=1,
        table_index=table_index,
        row_index=row_index,
        column_index=column_index,
        text=text,
        x0=x0,
        top=top,
        x1=x1,
        bottom=bottom,
    )
