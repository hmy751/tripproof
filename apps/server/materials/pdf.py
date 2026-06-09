from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


class PdfParseError(ValueError):
    """Raised when a PDF cannot produce usable text for TripProof."""


@dataclass(frozen=True)
class ParsedPdf:
    page_count: int
    text: str
    preview: str


def parse_pdf(raw: bytes) -> ParsedPdf:
    if not raw:
        raise PdfParseError("비어 있는 PDF입니다.")

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


def _clean_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _preview(text: str) -> str:
    single_line = " ".join(text.split())
    return single_line[:360]
