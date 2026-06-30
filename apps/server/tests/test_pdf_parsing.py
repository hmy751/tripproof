from __future__ import annotations

from server.materials.pdf import _clean_table_cell_text, _clean_text


def test_pdf_text_cleaning_collapses_duplicated_cjk_and_hangul_glyphs() -> None:
    assert (
        _clean_table_cell_text(
            "Country of Residence : 대대한한민민국국\n"
            "The Millennials 福福岡岡\n"
            "5-2-18 Nakasu, 하하카카타타, 후후쿠쿠오오카카, 일일본본"
        )
        == "Country of Residence : 대한민국\n"
        "The Millennials 福岡\n"
        "5-2-18 Nakasu, 하카타, 후쿠오카, 일본"
    )


def test_pdf_text_cleaning_collapses_duplicated_korean_date_units() -> None:
    assert (
        _clean_table_cell_text("2025년년 3월월 09일일\n체체크크인인: 체체크크아아웃웃:")
        == "2025년 3월 09일\n체크인: 체크아웃:"
    )


def test_pdf_text_cleaning_preserves_ascii_repeated_letters() -> None:
    text = "Booking coffee No-Show Wi-Fi room 100%"

    assert _clean_table_cell_text(text) == text
    assert _clean_text(text) == text
