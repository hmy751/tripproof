from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import median

from server.materials.layout import (
    BBox,
    PageLayout,
    PdfLine,
    PdfTableCell,
    PdfTableRow,
    bbox_for_lines,
    bbox_to_metadata,
)
from server.retrieval.models import SourceUnit


@dataclass(frozen=True)
class TextChunk:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class StructuralBlock:
    page: int
    block_index: int
    structural_kind: str
    lines: tuple[PdfLine, ...] = ()
    text_override: str | None = None
    bbox: BBox | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.text_override is None and not self.lines:
            raise ValueError("StructuralBlock must have lines or text_override.")
        if self.text_override is not None and self.bbox is None:
            raise ValueError("StructuralBlock with text_override must have a bbox.")

    @property
    def text(self) -> str:
        if self.text_override is not None:
            return self.text_override.strip()
        return "\n".join(line.text for line in self.lines if line.text).strip()

    @property
    def line_count(self) -> int:
        if self.lines:
            return len(self.lines)
        return len([line for line in self.text.splitlines() if line.strip()])


def chunk_text(
    text: str, *, chunk_size: int = 1200, overlap: int = 160
) -> list[TextChunk]:
    stripped = text.strip()
    if not stripped:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    while start < len(stripped):
        end = min(start + chunk_size, len(stripped))
        chunks.append(TextChunk(text=stripped[start:end], start=start, end=end))
        if end == len(stripped):
            break
        start = end - overlap
    return chunks


def build_source_units(
    *,
    material_id: str,
    file_name: str,
    text: str,
    layout_pages: tuple[PageLayout, ...] = (),
    chunk_size: int = 1200,
    overlap: int = 160,
) -> list[SourceUnit]:
    if layout_pages:
        units = _build_layout_source_units(
            material_id=material_id,
            file_name=file_name,
            layout_pages=layout_pages,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        if units:
            return units

    return _build_text_source_units(
        material_id=material_id,
        file_name=file_name,
        text=text,
        chunk_size=chunk_size,
        overlap=overlap,
    )


def _build_text_source_units(
    *,
    material_id: str,
    file_name: str,
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[SourceUnit]:
    units: list[SourceUnit] = []
    unit_index = 1

    for page, page_text in _iter_page_texts(text):
        for chunk in chunk_text(page_text, chunk_size=chunk_size, overlap=overlap):
            locator = _locator(file_name=file_name, page=page, unit_index=unit_index)
            units.append(
                SourceUnit(
                    id=f"su_{material_id}_{page}_{unit_index}",
                    material_id=material_id,
                    file_name=file_name,
                    page=page,
                    unit_index=unit_index,
                    locator=locator,
                    text=chunk.text,
                    search_text=_normalize_search_text(chunk.text),
                    start=chunk.start,
                    end=chunk.end,
                    metadata={
                        "page": page,
                        "extraction_backend": "pypdf_text",
                        "structural_kind": "text_chunk",
                        "kind": "general",
                        "fallback_used": True,
                    },
                )
            )
            unit_index += 1

    return units


def _build_layout_source_units(
    *,
    material_id: str,
    file_name: str,
    layout_pages: tuple[PageLayout, ...],
    chunk_size: int,
    overlap: int,
) -> list[SourceUnit]:
    blocks = _structural_blocks(layout_pages)
    units: list[SourceUnit] = []
    cursor = 0

    for block in blocks:
        block_text = block.text
        if not block_text:
            continue
        chunks = (
            [TextChunk(text=block_text, start=0, end=len(block_text))]
            if len(block_text) <= chunk_size
            else chunk_text(block_text, chunk_size=chunk_size, overlap=overlap)
        )
        block_bbox = bbox_to_metadata(_block_bbox(block))
        for split_index, chunk in enumerate(chunks, start=1):
            unit_index = len(units) + 1
            unit_text = chunk.text.strip()
            if not unit_text:
                continue
            start = cursor
            end = start + len(unit_text)
            locator = _locator(
                file_name=file_name, page=block.page, unit_index=unit_index
            )
            metadata = {
                "page": block.page,
                "block_index": block.block_index,
                "split_index": split_index,
                "extraction_backend": "pdfplumber",
                "structural_kind": block.structural_kind,
                "kind": _semantic_kind(unit_text, block.structural_kind),
                "bbox": block_bbox,
                "line_count": block.line_count,
                "fallback_used": False,
            }
            metadata.update(block.metadata)
            units.append(
                SourceUnit(
                    id=f"su_{material_id}_{block.page}_{unit_index}",
                    material_id=material_id,
                    file_name=file_name,
                    page=block.page,
                    unit_index=unit_index,
                    locator=locator,
                    text=unit_text,
                    search_text=_normalize_search_text(unit_text),
                    start=start,
                    end=end,
                    metadata=metadata,
                )
            )
            cursor = end + 2

    return units


def _structural_blocks(layout_pages: tuple[PageLayout, ...]) -> list[StructuralBlock]:
    blocks: list[StructuralBlock] = []
    for layout in layout_pages:
        page_blocks = _page_structural_blocks(layout)
        blocks.extend(page_blocks)
    return blocks


def _page_structural_blocks(layout: PageLayout) -> list[StructuralBlock]:
    line_blocks = _page_line_structural_blocks(layout)
    field_blocks = _page_field_group_blocks(layout=layout, line_blocks=line_blocks)
    return _renumber_blocks(field_blocks + line_blocks)


def _page_line_structural_blocks(layout: PageLayout) -> list[StructuralBlock]:
    lines = tuple(line for line in layout.lines if line.text.strip())
    if not lines:
        return []

    median_font_size = _median_font_size(lines)
    blocks: list[StructuralBlock] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        previous_line = lines[index - 1] if index > 0 else None
        next_line = lines[index + 1] if index + 1 < len(lines) else None

        if _is_key_value_line(line):
            block_lines = [line]
            if _should_attach_value_line(line, next_line):
                block_lines.append(next_line)
                index += 1
            blocks.append(_block(layout.page, "key_value_row", block_lines))
        elif _is_list_item(line):
            block_lines, index = _collect_continuation_lines(
                lines=lines,
                start_index=index,
                median_font_size=median_font_size,
                structural_kind="list_item",
            )
            blocks.append(_block(layout.page, "list_item", block_lines))
        elif _is_table_like_line(line, previous_line, next_line):
            blocks.append(_block(layout.page, "table_row", [line]))
        elif _is_heading_line(line, next_line, median_font_size):
            block_lines, index = _collect_heading_paragraph(
                lines=lines,
                start_index=index,
                median_font_size=median_font_size,
            )
            blocks.append(_block(layout.page, "heading_paragraph", block_lines))
        else:
            block_lines, index = _collect_paragraph_lines(
                lines=lines,
                start_index=index,
                median_font_size=median_font_size,
            )
            blocks.append(_block(layout.page, "paragraph", block_lines))

        index += 1

    return _merge_small_paragraphs(blocks)


def _page_field_group_blocks(
    *,
    layout: PageLayout,
    line_blocks: list[StructuralBlock],
) -> list[StructuralBlock]:
    table_blocks = _table_field_group_blocks(layout) if layout.table_rows else []
    covered_bboxes = [block.bbox for block in table_blocks if block.bbox is not None]
    section_blocks = _small_section_field_group_blocks(
        line_blocks=line_blocks,
        covered_bboxes=covered_bboxes,
    )
    return _deduplicate_field_blocks(table_blocks + section_blocks)


def _table_field_group_blocks(layout: PageLayout) -> list[StructuralBlock]:
    blocks: list[StructuralBlock] = []
    for row in layout.table_rows:
        if _is_significant_table_row(row=row, layout=layout):
            blocks.append(_table_row_block(row))
        for cell in row.cells:
            if _is_significant_table_cell(cell=cell, layout=layout):
                blocks.append(_table_cell_block(cell))
    return blocks


def _table_row_block(row: PdfTableRow) -> StructuralBlock:
    return StructuralBlock(
        page=row.page,
        block_index=0,
        structural_kind="table_row_group",
        text_override=row.text,
        bbox=row.bbox,
        metadata={
            "layout_source": "pdfplumber_table_row",
            "table_index": row.table_index,
            "row_index": row.row_index,
            "cell_count": len(row.cells),
            "source_text_role": "layout_derived_region",
            "source_fragment_count": len(row.cells),
            "source_fragments": [_cell_source_fragment(cell) for cell in row.cells],
        },
    )


def _table_cell_block(cell: PdfTableCell) -> StructuralBlock:
    return StructuralBlock(
        page=cell.page,
        block_index=0,
        structural_kind="field_group",
        text_override=cell.text,
        bbox=cell.bbox,
        metadata={
            "layout_source": "pdfplumber_table_cell",
            "table_index": cell.table_index,
            "row_index": cell.row_index,
            "column_index": cell.column_index,
            "cell_count": 1,
            "source_text_role": "layout_derived_region",
            "source_fragment_count": 1,
            "source_fragments": [_cell_source_fragment(cell)],
        },
    )


def _is_significant_table_row(*, row: PdfTableRow, layout: PageLayout) -> bool:
    text = _normalize_search_text(row.text)
    if len(row.cells) < 3 or len(text) < 36 or row.line_count < 3:
        return False
    if _bbox_height(row.bbox) > layout.height * 0.16:
        return False
    return True


def _is_significant_table_cell(*, cell: PdfTableCell, layout: PageLayout) -> bool:
    text = _normalize_search_text(cell.text)
    width = _bbox_width(cell.bbox)
    height = _bbox_height(cell.bbox)
    if len(text) < 32 or width < 72 or height < 16:
        return False
    if cell.line_count < 3 and not _has_label_separator(cell.text):
        return False
    if height > layout.height * 0.35:
        return False
    if width > layout.width * 0.96 and height > layout.height * 0.12:
        return False
    if cell.line_count > max(4, int(height / 5.5) + 2):
        return False
    return True


def _small_section_field_group_blocks(
    *,
    line_blocks: list[StructuralBlock],
    covered_bboxes: list[BBox],
) -> list[StructuralBlock]:
    groups: list[StructuralBlock] = []
    current: list[StructuralBlock] = []
    skipped_bridge: StructuralBlock | None = None

    def flush_current() -> None:
        nonlocal current, skipped_bridge
        group = _small_section_group_block(current)
        if group is not None:
            groups.append(group)
        current = []
        skipped_bridge = None

    for block in line_blocks:
        if _covered_by_any_bbox(_block_bbox(block), covered_bboxes):
            flush_current()
            continue
        if not _is_small_section_candidate(block):
            if current and _is_complete_single_line_key_value_block(block):
                if _can_skip_small_section_bridge(current, block):
                    skipped_bridge = block
                    continue
            flush_current()
            continue
        previous_block = skipped_bridge or current[-1] if current else None
        if (
            current
            and previous_block is not None
            and not _can_extend_small_section(
                current=current,
                candidate=block,
                previous=previous_block,
            )
        ):
            flush_current()
        current.append(block)
        skipped_bridge = None

    flush_current()
    return groups


def _small_section_group_block(
    blocks: list[StructuralBlock],
) -> StructuralBlock | None:
    if sum(block.line_count for block in blocks) < 3:
        return None
    bbox = _union_bbox([_block_bbox(block) for block in blocks])
    if _bbox_height(bbox) > 140:
        return None
    text = "\n".join(block.text for block in blocks if block.text).strip()
    if len(_normalize_search_text(text)) < 40:
        return None
    return StructuralBlock(
        page=blocks[0].page,
        block_index=0,
        structural_kind="field_group",
        text_override=text,
        bbox=bbox,
        metadata={
            "layout_source": "line_region",
            "group_block_count": len(blocks),
            "source_text_role": "layout_derived_region",
            "source_fragment_count": sum(len(block.lines) for block in blocks),
            "source_fragments": _line_source_fragments(blocks),
        },
    )


def _is_small_section_candidate(block: StructuralBlock) -> bool:
    if _is_complete_single_line_key_value_block(block):
        return False
    return (
        block.structural_kind in {"key_value_row", "paragraph", "heading_paragraph"}
        and block.line_count <= 2
        and 4 <= len(_normalize_search_text(block.text)) <= 120
    )


def _is_complete_single_line_key_value_block(block: StructuralBlock) -> bool:
    if block.structural_kind != "key_value_row" or block.line_count != 1:
        return False
    text = block.text.strip()
    separator_indexes = [
        index for index in (text.find(":"), text.find("：")) if index >= 0
    ]
    if not separator_indexes:
        return False
    separator_index = min(separator_indexes)
    return bool(text[separator_index + 1 :].strip())


def _can_skip_small_section_bridge(
    current: list[StructuralBlock],
    bridge: StructuralBlock,
) -> bool:
    if not current:
        return False
    previous = current[-1]
    if previous.page != bridge.page:
        return False
    if _vertical_gap_between_blocks(previous, bridge) > 32:
        return False
    return _blocks_share_visual_column(previous, bridge)


def _can_extend_small_section(
    *,
    current: list[StructuralBlock],
    candidate: StructuralBlock,
    previous: StructuralBlock | None = None,
) -> bool:
    previous = previous or current[-1]
    if previous.page != candidate.page:
        return False
    if _vertical_gap_between_blocks(previous, candidate) > 32:
        return False
    candidate_bbox = _block_bbox(candidate)
    span_bbox = _union_bbox(
        [_block_bbox(block) for block in current] + [candidate_bbox]
    )
    if _bbox_height(span_bbox) > 140:
        return False
    return _blocks_share_visual_column(previous, candidate)


def _deduplicate_field_blocks(blocks: list[StructuralBlock]) -> list[StructuralBlock]:
    deduplicated: list[StructuralBlock] = []
    for block in blocks:
        normalized = _normalize_search_text(block.text).casefold()
        if not normalized:
            continue
        if any(
            _is_overlapping_duplicate_field_block(block, existing)
            for existing in deduplicated
        ):
            continue
        deduplicated.append(block)
    return deduplicated


def _is_overlapping_duplicate_field_block(
    block: StructuralBlock,
    existing: StructuralBlock,
) -> bool:
    if block.page != existing.page:
        return False
    if (
        _normalize_search_text(block.text).casefold()
        != _normalize_search_text(existing.text).casefold()
    ):
        return False
    block_area = _bbox_area(_block_bbox(block))
    existing_area = _bbox_area(_block_bbox(existing))
    if min(block_area, existing_area) <= 0:
        return False
    overlap = _bbox_overlap_area(_block_bbox(block), _block_bbox(existing))
    return overlap / min(block_area, existing_area) >= 0.72


def _cell_source_fragment(cell: PdfTableCell) -> dict[str, object]:
    return {
        "layout_source": "pdfplumber_table_cell",
        "text": cell.text,
        "bbox": bbox_to_metadata(cell.bbox),
        "table_index": cell.table_index,
        "row_index": cell.row_index,
        "column_index": cell.column_index,
    }


def _line_source_fragments(blocks: list[StructuralBlock]) -> list[dict[str, object]]:
    return [
        {
            "layout_source": "pdfplumber_line",
            "text": line.text,
            "bbox": bbox_to_metadata(line.bbox),
            "line_order": line.order,
        }
        for block in blocks
        for line in block.lines
    ]


def _block(page: int, structural_kind: str, lines: list[PdfLine]) -> StructuralBlock:
    return StructuralBlock(
        page=page,
        block_index=0,
        structural_kind=structural_kind,
        lines=tuple(lines),
    )


def _collect_heading_paragraph(
    *,
    lines: tuple[PdfLine, ...],
    start_index: int,
    median_font_size: float,
) -> tuple[list[PdfLine], int]:
    block_lines = [lines[start_index]]
    index = start_index
    while index + 1 < len(lines):
        current = lines[index]
        candidate = lines[index + 1]
        if _is_hard_boundary(candidate, current, median_font_size):
            break
        if _vertical_gap(current, candidate) > _paragraph_gap_limit(current):
            break
        block_lines.append(candidate)
        index += 1
    return block_lines, index


def _collect_continuation_lines(
    *,
    lines: tuple[PdfLine, ...],
    start_index: int,
    median_font_size: float,
    structural_kind: str,
) -> tuple[list[PdfLine], int]:
    block_lines = [lines[start_index]]
    index = start_index
    while index + 1 < len(lines):
        current = lines[index]
        candidate = lines[index + 1]
        if _vertical_gap(current, candidate) > _paragraph_gap_limit(current):
            break
        if structural_kind == "list_item" and _is_list_item(candidate):
            break
        if _is_key_value_line(candidate) or _is_heading_line(
            candidate,
            lines[index + 2] if index + 2 < len(lines) else None,
            median_font_size,
        ):
            break
        if candidate.x0 < block_lines[0].x0 - 2:
            break
        block_lines.append(candidate)
        index += 1
    return block_lines, index


def _collect_paragraph_lines(
    *,
    lines: tuple[PdfLine, ...],
    start_index: int,
    median_font_size: float,
) -> tuple[list[PdfLine], int]:
    block_lines = [lines[start_index]]
    index = start_index
    while index + 1 < len(lines):
        current = lines[index]
        candidate = lines[index + 1]
        next_candidate = lines[index + 2] if index + 2 < len(lines) else None
        if _vertical_gap(current, candidate) > _paragraph_gap_limit(current):
            break
        if _is_key_value_line(candidate):
            break
        if _is_table_like_line(candidate, current, next_candidate):
            break
        if _is_list_item(candidate):
            break
        if _is_heading_line(candidate, next_candidate, median_font_size):
            break
        if abs(candidate.x0 - block_lines[0].x0) > 28 and candidate.x0 < current.x0:
            break
        block_lines.append(candidate)
        index += 1
    return block_lines, index


def _is_hard_boundary(
    line: PdfLine,
    previous_line: PdfLine,
    median_font_size: float,
) -> bool:
    return (
        _is_key_value_line(line)
        or _is_table_like_line(line, previous_line, None)
        or _is_list_item(line)
        or _is_heading_line(line, None, median_font_size)
    )


def _merge_small_paragraphs(blocks: list[StructuralBlock]) -> list[StructuralBlock]:
    merged: list[StructuralBlock] = []
    for block in blocks:
        text = block.text
        if (
            merged
            and block.structural_kind == "paragraph"
            and len(text) < 24
            and merged[-1].page == block.page
            and merged[-1].structural_kind in {"heading_paragraph", "paragraph"}
            and _vertical_gap(merged[-1].lines[-1], block.lines[0])
            <= _paragraph_gap_limit(merged[-1].lines[-1])
        ):
            previous = merged[-1]
            merged[-1] = StructuralBlock(
                page=previous.page,
                block_index=previous.block_index,
                structural_kind=previous.structural_kind,
                lines=previous.lines + block.lines,
            )
            continue
        merged.append(block)
    return merged


def _renumber_blocks(blocks: list[StructuralBlock]) -> list[StructuralBlock]:
    return [
        StructuralBlock(
            page=block.page,
            block_index=index,
            structural_kind=block.structural_kind,
            lines=block.lines,
            text_override=block.text_override,
            bbox=block.bbox,
            metadata=block.metadata,
        )
        for index, block in enumerate(blocks, start=1)
    ]


def _is_key_value_line(line: PdfLine) -> bool:
    text = line.text.strip()
    if _has_label_separator(text):
        separator_index = min(
            [index for index in (text.find(":"), text.find("：")) if index >= 0]
        )
        return 0 < separator_index <= 48
    return (
        _large_gap_count(line) == 1
        and len(line.words) >= 2
        and not _looks_like_sentence(text)
    )


def _should_attach_value_line(line: PdfLine, next_line: PdfLine | None) -> bool:
    if next_line is None:
        return False
    if not line.text.rstrip().endswith((":", "：")):
        return False
    return (
        _vertical_gap(line, next_line) <= _paragraph_gap_limit(line)
        and next_line.x0 >= line.x0 + 8
        and not _is_key_value_line(next_line)
    )


def _is_table_like_line(
    line: PdfLine,
    previous_line: PdfLine | None,
    next_line: PdfLine | None,
) -> bool:
    if _is_list_item(line) or _looks_like_sentence(line.text):
        return False
    if _large_gap_count(line) < 2:
        return False
    return _shares_column_starts(line, previous_line) or _shares_column_starts(
        line, next_line
    )


def _is_list_item(line: PdfLine) -> bool:
    return bool(re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line.text))


def _is_heading_line(
    line: PdfLine,
    next_line: PdfLine | None,
    median_font_size: float,
) -> bool:
    text = line.text.strip()
    if not text or _is_key_value_line(line):
        return False
    if line.font_size is not None and line.font_size >= median_font_size + 1.5:
        return True
    if next_line is None:
        return False
    return (
        len(text) <= 52
        and not _looks_like_sentence(text)
        and _vertical_gap(line, next_line) <= _paragraph_gap_limit(line)
        and next_line.x0 >= line.x0 - 2
    )


def _looks_like_sentence(text: str) -> bool:
    stripped = text.strip()
    return stripped.endswith((".", "?", "!", "다", "요"))


def _large_gap_count(line: PdfLine) -> int:
    words = sorted(line.words, key=lambda word: word.x0)
    gaps = [words[index + 1].x0 - words[index].x1 for index in range(len(words) - 1)]
    return sum(gap >= 32 for gap in gaps)


def _shares_column_starts(line: PdfLine, other: PdfLine | None) -> bool:
    if other is None:
        return False
    starts = [word.x0 for word in sorted(line.words, key=lambda word: word.x0)]
    other_starts = [word.x0 for word in sorted(other.words, key=lambda word: word.x0)]
    matches = 0
    for start in starts[:4]:
        if any(abs(start - other_start) <= 8 for other_start in other_starts[:4]):
            matches += 1
    return matches >= 2


def _has_label_separator(text: str) -> bool:
    return ":" in text or "：" in text


def _block_bbox(block: StructuralBlock) -> BBox:
    if block.bbox is not None:
        return block.bbox
    return bbox_for_lines(block.lines)


def _union_bbox(bboxes: list[BBox]) -> BBox:
    return (
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    )


def _bbox_width(bbox: BBox) -> float:
    return max(0.0, bbox[2] - bbox[0])


def _bbox_height(bbox: BBox) -> float:
    return max(0.0, bbox[3] - bbox[1])


def _bbox_area(bbox: BBox) -> float:
    return _bbox_width(bbox) * _bbox_height(bbox)


def _bbox_overlap_area(first: BBox, second: BBox) -> float:
    x_overlap = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    y_overlap = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    return x_overlap * y_overlap


def _covered_by_any_bbox(bbox: BBox, candidates: list[BBox]) -> bool:
    area = _bbox_area(bbox)
    if area <= 0:
        return False
    return any(
        _bbox_overlap_area(bbox, candidate) / area >= 0.72 for candidate in candidates
    )


def _vertical_gap_between_blocks(
    previous: StructuralBlock,
    candidate: StructuralBlock,
) -> float:
    previous_bbox = _block_bbox(previous)
    candidate_bbox = _block_bbox(candidate)
    return max(0.0, candidate_bbox[1] - previous_bbox[3])


def _blocks_share_visual_column(
    first: StructuralBlock,
    second: StructuralBlock,
) -> bool:
    first_bbox = _block_bbox(first)
    second_bbox = _block_bbox(second)
    x_overlap = max(
        0.0, min(first_bbox[2], second_bbox[2]) - max(first_bbox[0], second_bbox[0])
    )
    narrower_width = max(1.0, min(_bbox_width(first_bbox), _bbox_width(second_bbox)))
    return (
        x_overlap / narrower_width >= 0.6 or abs(first_bbox[0] - second_bbox[0]) <= 10
    )


def _vertical_gap(previous_line: PdfLine, next_line: PdfLine) -> float:
    return max(0.0, next_line.top - previous_line.bottom)


def _paragraph_gap_limit(line: PdfLine) -> float:
    return max(7.0, line.height * 1.5)


def _median_font_size(lines: tuple[PdfLine, ...]) -> float:
    sizes = [line.font_size for line in lines if line.font_size is not None]
    return float(median(sizes)) if sizes else 10.0


def _semantic_kind(text: str, structural_kind: str) -> str:
    normalized = text.casefold()
    if structural_kind == "key_value_row":
        return "label_value"
    if _contains_any(
        normalized,
        ("취소", "노쇼", "no-show", "refund", "cancellation", "cancel"),
    ):
        return "policy"
    if _contains_any(
        normalized,
        ("중요", "알림", "주의", "반드시", "required", "important", "notice"),
    ):
        return "warning"
    if _contains_any(
        normalized,
        ("요청", "remarks", "request", "preference"),
    ):
        return "request_note"
    if _contains_any(
        normalized,
        ("세금", "도시세", "요금", "비용", "fee", "tax", "payment", "charge"),
    ):
        return "fee"
    if structural_kind in {"field_group", "table_row_group"}:
        return "label_value"
    return "general"


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _iter_page_texts(text: str) -> list[tuple[int, str]]:
    stripped = text.strip()
    if not stripped:
        return []

    lines = stripped.splitlines()
    markers = [
        (index, page)
        for index, line in enumerate(lines)
        if (page := _page_marker_number(line)) is not None
    ]
    if not markers:
        return [(1, stripped)]

    pages: list[tuple[int, str]] = []
    for index, (line_index, page) in enumerate(markers):
        body_start = line_index + 1
        body_end = markers[index + 1][0] if index + 1 < len(markers) else len(lines)
        page_text = "\n".join(lines[body_start:body_end]).strip()
        if page_text:
            pages.append((page, page_text))
    return pages


def _page_marker_number(line: str) -> int | None:
    stripped = line.strip()
    if not stripped.startswith("[page ") or not stripped.endswith("]"):
        return None
    value = stripped.removeprefix("[page ").removesuffix("]").strip()
    return int(value) if value.isdigit() else None


def _locator(*, file_name: str, page: int, unit_index: int) -> str:
    return f"{file_name} p.{page} u.{unit_index}"


def _normalize_search_text(text: str) -> str:
    return " ".join(text.split())
