from __future__ import annotations

from dataclasses import dataclass
from statistics import median

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class PdfWord:
    page: int
    text: str
    x0: float
    top: float
    x1: float
    bottom: float
    order: int
    font_name: str | None = None
    size: float | None = None

    @property
    def bbox(self) -> BBox:
        return (self.x0, self.top, self.x1, self.bottom)


@dataclass(frozen=True)
class PdfLine:
    page: int
    text: str
    words: tuple[PdfWord, ...]
    x0: float
    top: float
    x1: float
    bottom: float
    order: int
    font_size: float | None = None

    @property
    def bbox(self) -> BBox:
        return (self.x0, self.top, self.x1, self.bottom)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)


@dataclass(frozen=True)
class PdfTableCell:
    page: int
    table_index: int
    row_index: int
    column_index: int
    text: str
    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def bbox(self) -> BBox:
        return (self.x0, self.top, self.x1, self.bottom)

    @property
    def line_count(self) -> int:
        return len([line for line in self.text.splitlines() if line.strip()])


@dataclass(frozen=True)
class PdfTableRow:
    page: int
    table_index: int
    row_index: int
    cells: tuple[PdfTableCell, ...]
    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def bbox(self) -> BBox:
        return (self.x0, self.top, self.x1, self.bottom)

    @property
    def text(self) -> str:
        return "\n".join(cell.text for cell in self.cells if cell.text).strip()

    @property
    def line_count(self) -> int:
        return sum(cell.line_count for cell in self.cells)


@dataclass(frozen=True)
class PageLayout:
    page: int
    width: float
    height: float
    lines: tuple[PdfLine, ...]
    table_rows: tuple[PdfTableRow, ...] = ()


def build_lines_from_words(
    *,
    page: int,
    words: list[PdfWord],
    y_tolerance: float = 3.0,
) -> tuple[PdfLine, ...]:
    sorted_words = sorted(words, key=lambda word: (word.top, word.x0, word.order))
    if not sorted_words:
        return ()

    grouped: list[list[PdfWord]] = []
    current: list[PdfWord] = []
    current_top = 0.0

    for word in sorted_words:
        if not current:
            current = [word]
            current_top = word.top
            continue
        tolerance = max(y_tolerance, _median_word_size(current) * 0.35)
        if abs(word.top - current_top) <= tolerance:
            current.append(word)
            current_top = median([item.top for item in current])
            continue
        grouped.append(sorted(current, key=lambda item: (item.x0, item.order)))
        current = [word]
        current_top = word.top

    if current:
        grouped.append(sorted(current, key=lambda item: (item.x0, item.order)))

    return tuple(
        PdfLine(
            page=page,
            text=_join_words(line_words),
            words=tuple(line_words),
            x0=min(word.x0 for word in line_words),
            top=min(word.top for word in line_words),
            x1=max(word.x1 for word in line_words),
            bottom=max(word.bottom for word in line_words),
            order=index,
            font_size=_median_word_size(line_words),
        )
        for index, line_words in enumerate(grouped, start=1)
        if _join_words(line_words)
    )


def bbox_for_lines(lines: list[PdfLine] | tuple[PdfLine, ...]) -> BBox:
    return (
        min(line.x0 for line in lines),
        min(line.top for line in lines),
        max(line.x1 for line in lines),
        max(line.bottom for line in lines),
    )


def bbox_to_metadata(bbox: BBox) -> list[float]:
    return [round(value, 2) for value in bbox]


def _median_word_size(words: list[PdfWord]) -> float:
    sizes = [word.size for word in words if word.size is not None]
    return float(median(sizes)) if sizes else 10.0


def _join_words(words: list[PdfWord]) -> str:
    ordered = sorted(words, key=lambda word: (word.x0, word.order))
    return " ".join(word.text.strip() for word in ordered if word.text.strip()).strip()
