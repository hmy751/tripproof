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
    assert units[0].metadata["source_text_role"] == "layout_derived_region"
    assert units[0].metadata["source_fragment_count"] == 4
    assert len(units[0].metadata["source_fragments"]) == 4
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
            _table_row(
                row_index=2,
                cells=[
                    _cell(
                        "The Millennials Fukuoka\n5-2-18 Nakasu, Fukuoka\nJapan 810-0801",
                        column_index=1,
                        row_index=2,
                        x0=130,
                        top=82,
                        x1=360,
                        bottom=152,
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
    assert units[0].metadata["source_text_role"] == "layout_derived_region"
    assert units[0].metadata["source_fragment_count"] == 1
    assert "Number of Rooms" in units[0].text
    assert "Number of Adults" in units[0].text
    assert "Number of Children" in units[0].text
    assert "Room Type" in units[0].text


def test_layout_source_units_keep_repeated_table_cell_text_in_distinct_regions() -> (
    None
):
    repeated_text = "Policy :\nSame value applies.\nContact the desk for details."
    layout = _page_layout(
        [],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        repeated_text,
                        column_index=1,
                        x0=72,
                        top=70,
                        x1=320,
                        bottom=116,
                    ),
                ],
            ),
            _table_row(
                row_index=2,
                cells=[
                    _cell(
                        repeated_text,
                        column_index=1,
                        row_index=2,
                        x0=72,
                        top=150,
                        x1=320,
                        bottom=196,
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

    repeated_units = [
        unit
        for unit in units
        if unit.metadata.get("layout_source") == "pdfplumber_table_cell"
    ]
    assert len(repeated_units) == 2
    assert [unit.metadata["row_index"] for unit in repeated_units] == [1, 2]
    assert repeated_units[0].metadata["bbox"] != repeated_units[1].metadata["bbox"]


def test_layout_source_units_add_uncovered_small_section_field_group() -> None:
    layout = _page_layout(
        [
            _line("Header A : Header B :", top=72, words_x=[72, 220]),
            _line("111 222", top=84, words_x=[140, 300]),
            _line("Section A :", top=180),
            _line("Alpha value", top=194, words_x=[124, 172]),
            _line("Reference ID : ABC-123", top=226),
            _line("Beta value", top=244, words_x=[124, 172]),
            _line("Gamma value", top=262, words_x=[124, 172]),
            _line("Next Section", top=308, size=16),
            _line("Outside value", top=332),
        ],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        "Header A :\n111\nHeader B :\n222",
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
    assert request_group.metadata["source_text_role"] == "layout_derived_region"
    assert "Section A" in request_group.text
    assert "Alpha value" in request_group.text
    assert "Beta value" in request_group.text
    assert "Gamma value" in request_group.text
    assert "Header A" not in request_group.text
    assert "Reference ID" not in request_group.text
    assert "Next Section" not in request_group.text


def test_layout_source_units_do_not_add_line_region_for_table_covered_columns() -> None:
    layout = _page_layout(
        [
            _line(
                "Booking ID : 1555887916 Number of Rooms :",
                top=72,
                words_x=[72, 120, 135, 165, 360, 425, 450, 505],
            ),
            _line("1", top=84, words_x=[520]),
            _line(
                "예약 번호 : 객실 수 :",
                top=96,
                words_x=[72, 120, 150, 360, 405, 435],
            ),
            _line(
                "Booking Reference No : Number of Extra Beds :",
                top=116,
                words_x=[72, 135, 210, 245, 360, 425, 445, 500, 555],
            ),
            _line("0", top=128, words_x=[520]),
            _line(
                "예약 참조 번호 : 간이 침대 수 :",
                top=140,
                words_x=[72, 115, 155, 190, 360, 405, 445, 475],
            ),
        ],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        (
                            "Booking ID : 1555887916\n예약 번호 :\n"
                            "Booking Reference No :\n예약 참조 번호 :"
                        ),
                        column_index=1,
                        x0=70,
                        top=68,
                        x1=300,
                        bottom=154,
                    ),
                    _cell(
                        (
                            "Number of Rooms :\n1\n객실 수 :\n"
                            "Number of Extra Beds :\n0\n간이 침대 수 :"
                        ),
                        column_index=2,
                        x0=350,
                        top=68,
                        x1=590,
                        bottom=154,
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

    line_regions = [
        unit for unit in units if unit.metadata.get("layout_source") == "line_region"
    ]
    assert all("Booking ID" not in unit.text for unit in line_regions)
    assert all("Number of Extra Beds" not in unit.text for unit in line_regions)


def test_layout_source_units_keep_wide_field_group_with_values() -> None:
    layout = _page_layout(
        [
            _line("Property :", top=72, words_x=[72, 130]),
            _line(
                "The Millennials Fukuoka near Nakasu Hakata",
                top=86,
                words_x=[132, 188, 260, 340, 415, 475],
            ),
            _line("숙소명 :", top=104, words_x=[72, 120]),
            _line("Address :", top=122, words_x=[72, 130]),
            _line(
                "5-2-18 Nakasu, Hakata, Fukuoka, Japan, 810-0801",
                top=136,
                words_x=[132, 205, 275, 350, 420, 485],
            ),
            _line("주소 :", top=154, words_x=[72, 118]),
        ],
        table_rows=(
            _table_row(
                row_index=1,
                cells=[
                    _cell(
                        (
                            "Booking ID : 1555887916\n예약 번호:\n"
                            "Client : MYEONGYEON HAM\n고객명 :\n"
                            "Property : The Millennials Fukuoka\n숙소명:\n"
                            "Address : 5-2-18 Nakasu, Fukuoka\n주소:\n"
                            "Property Contact Number : ++81922622009\n숙소 연락처:"
                        ),
                        column_index=1,
                        x0=70,
                        top=68,
                        x1=590,
                        bottom=180,
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

    line_region = next(
        unit for unit in units if unit.metadata.get("layout_source") == "line_region"
    )
    assert "Property" in line_region.text
    assert "The Millennials Fukuoka" in line_region.text
    assert "Address" in line_region.text
    assert "810-0801" in line_region.text


def test_layout_source_units_add_line_region_field_group_without_tables() -> None:
    layout = _page_layout(
        [
            _line("Section A :", top=72),
            _line("Alpha value", top=86, words_x=[124, 172]),
            _line("Section B :", top=104),
            _line("Beta value", top=118, words_x=[124, 172]),
            _line("Section C :", top=136),
            _line("Gamma value", top=150, words_x=[124, 172]),
        ]
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    line_region = next(
        unit for unit in units if unit.metadata.get("layout_source") == "line_region"
    )
    assert line_region.metadata["structural_kind"] == "field_group"
    assert line_region.metadata["source_text_role"] == "layout_derived_region"
    assert line_region.metadata["source_fragment_count"] == 6
    assert len(line_region.metadata["source_fragments"]) == 6
    assert "Section A" in line_region.text
    assert "Alpha value" in line_region.text
    assert "Section C" in line_region.text


def test_layout_source_units_keep_wide_sentence_line_region() -> None:
    layout = _page_layout(
        [
            _line("Remarks :", top=72),
            _line("NonSmoke,LargeBed", top=86),
            _line("City tax notice", top=104),
            _line(
                "Local tax may be charged and paid directly at check in.",
                top=118,
            ),
            _line("Guest list : MYEONGYEON HAM", top=146),
            _line(
                "Special requests are subject to property availability.",
                top=164,
            ),
        ]
    )

    units = build_source_units(
        material_id="mat_1",
        file_name="booking.pdf",
        text="[page 1]\nignored text",
        layout_pages=(layout,),
    )

    line_region = next(
        unit for unit in units if unit.metadata.get("layout_source") == "line_region"
    )
    assert "Remarks" in line_region.text
    assert "NonSmoke,LargeBed" in line_region.text
    assert "Special requests" in line_region.text


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
