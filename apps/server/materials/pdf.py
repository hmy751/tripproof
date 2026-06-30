from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pdfplumber
from pypdf import PdfReader

from server.materials.layout import (
    PageLayout,
    PdfTableCell,
    PdfTableRow,
    PdfWord,
    build_lines_from_words,
)


class PdfParseError(ValueError):
    """Raised when a PDF cannot produce usable text for TripProof."""


@dataclass(frozen=True)
class ParsedPdf:
    page_count: int
    text: str
    preview: str
    layout_pages: tuple[PageLayout, ...] = ()


_TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
}


def parse_pdf(raw: bytes) -> ParsedPdf:
    if not raw:
        raise PdfParseError("비어 있는 PDF입니다.")

    try:
        parsed = _parse_pdf_with_pdfplumber(raw)
        if parsed.text.strip():
            return parsed
    except Exception:
        pass

    return _parse_pdf_with_pypdf(raw)


def _parse_pdf_with_pdfplumber(raw: bytes) -> ParsedPdf:
    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            layout_pages = tuple(
                _page_layout_from_pdfplumber_page(page=page, page_number=index)
                for index, page in enumerate(pdf.pages, start=1)
            )
    except Exception:
        raise

    page_texts = [
        f"[page {layout.page}]\n{_text_from_layout_page(layout)}"
        for layout in layout_pages
        if _text_from_layout_page(layout)
    ]
    text = "\n\n".join(page_texts).strip()
    if not text:
        raise PdfParseError("텍스트를 추출할 수 없는 PDF입니다.")

    return ParsedPdf(
        page_count=len(layout_pages),
        text=text,
        preview=_preview(text),
        layout_pages=layout_pages,
    )


def _parse_pdf_with_pypdf(raw: bytes) -> ParsedPdf:
    try:
        reader = PdfReader(BytesIO(raw))
    except Exception as error:  # pypdf raises several parser-specific exceptions.
        raise PdfParseError("PDF를 열 수 없습니다.") from error

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
        except Exception as error:
            raise PdfParseError("암호화된 PDF는 아직 지원하지 않습니다.") from error
        if decrypt_result == 0:
            raise PdfParseError("암호화된 PDF는 아직 지원하지 않습니다.")

    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        cleaned = _clean_text(extracted)
        if cleaned:
            page_texts.append(f"[page {index}]\n{cleaned}")

    text = "\n\n".join(page_texts).strip()
    if not text:
        raise PdfParseError("텍스트를 추출할 수 없는 PDF입니다.")

    return ParsedPdf(
        page_count=len(reader.pages),
        text=text,
        preview=_preview(text),
    )


def _page_layout_from_pdfplumber_page(
    *,
    page: Any,
    page_number: int,
) -> PageLayout:
    words = [
        PdfWord(
            page=page_number,
            text=_normalize_pdf_text_artifacts(str(raw_word.get("text") or "")),
            x0=float(raw_word.get("x0") or 0.0),
            top=float(raw_word.get("top") or 0.0),
            x1=float(raw_word.get("x1") or 0.0),
            bottom=float(raw_word.get("bottom") or 0.0),
            order=index,
            font_name=_string_or_none(raw_word.get("fontname")),
            size=_float_or_none(raw_word.get("size")),
        )
        for index, raw_word in enumerate(
            page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                extra_attrs=["fontname", "size"],
            ),
            start=1,
        )
        if str(raw_word.get("text") or "").strip()
    ]
    return PageLayout(
        page=page_number,
        width=float(page.width),
        height=float(page.height),
        lines=build_lines_from_words(page=page_number, words=words),
        table_rows=_table_rows_from_pdfplumber_page(
            page=page,
            page_number=page_number,
        ),
    )


def _table_rows_from_pdfplumber_page(
    *,
    page: Any,
    page_number: int,
) -> tuple[PdfTableRow, ...]:
    try:
        tables = page.find_tables(table_settings=_TABLE_SETTINGS)
    except Exception:
        return ()

    rows: list[PdfTableRow] = []
    for table_index, table in enumerate(tables, start=1):
        try:
            extracted_rows = table.extract()
        except Exception:
            extracted_rows = []
        for row_index, row in enumerate(table.rows, start=1):
            extracted_row = (
                extracted_rows[row_index - 1]
                if row_index - 1 < len(extracted_rows)
                else []
            )
            cells = _table_cells_from_pdfplumber_row(
                page_number=page_number,
                table_index=table_index,
                row_index=row_index,
                row=row,
                extracted_row=extracted_row,
            )
            if not cells:
                continue
            rows.append(
                PdfTableRow(
                    page=page_number,
                    table_index=table_index,
                    row_index=row_index,
                    cells=tuple(cells),
                    x0=min(cell.x0 for cell in cells),
                    top=min(cell.top for cell in cells),
                    x1=max(cell.x1 for cell in cells),
                    bottom=max(cell.bottom for cell in cells),
                )
            )
    return tuple(rows)


def _table_cells_from_pdfplumber_row(
    *,
    page_number: int,
    table_index: int,
    row_index: int,
    row: Any,
    extracted_row: list[str | None],
) -> list[PdfTableCell]:
    cells: list[PdfTableCell] = []
    for column_index, bbox in enumerate(row.cells, start=1):
        if bbox is None:
            continue
        text = _clean_table_cell_text(
            extracted_row[column_index - 1]
            if column_index - 1 < len(extracted_row)
            else None
        )
        if not text:
            continue
        x0, top, x1, bottom = bbox
        cells.append(
            PdfTableCell(
                page=page_number,
                table_index=table_index,
                row_index=row_index,
                column_index=column_index,
                text=text,
                x0=float(x0),
                top=float(top),
                x1=float(x1),
                bottom=float(bottom),
            )
        )
    return cells


def _text_from_layout_page(layout: PageLayout) -> str:
    return "\n".join(line.text for line in layout.lines if line.text).strip()


def _clean_text(text: str) -> str:
    normalized = _normalize_pdf_text_artifacts(text)
    lines = [" ".join(line.split()) for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _clean_table_cell_text(text: str | None) -> str:
    if text is None:
        return ""
    normalized = _normalize_pdf_text_artifacts(str(text))
    lines = [" ".join(line.split()) for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _normalize_pdf_text_artifacts(text: str) -> str:
    if not text:
        return text

    collapsed: list[str] = []
    for character in text:
        if (
            collapsed
            and character == collapsed[-1]
            and _is_cjk_or_hangul_syllable(character)
        ):
            continue
        collapsed.append(character)
    return "".join(collapsed)


def _is_cjk_or_hangul_syllable(character: str) -> bool:
    return (
        "\u3040" <= character <= "\u30ff"
        or "\u3400" <= character <= "\u9fff"
        or "\uf900" <= character <= "\ufaff"
        or "\uac00" <= character <= "\ud7af"
    )


def _preview(text: str) -> str:
    single_line = " ".join(text.split())
    return single_line[:360]


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
