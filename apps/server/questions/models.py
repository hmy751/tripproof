from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from server.answers.models import ChatAnswer

QuestionStatus = Literal["accepted", "blocked"]


@dataclass(frozen=True)
class QuestionAnswerResult:
    status: QuestionStatus
    message: str
    answer: ChatAnswer
    material_ids: list[str]
    material_count: int
    page_count: int
    char_count: int
