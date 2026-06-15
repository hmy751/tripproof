from __future__ import annotations

from server.answers.models import ChatAnswer
from server.questions.models import QuestionAnswerResult
from server.use_cases.question_scope import MaterialScopeSelection


class QuestionAnswerPresenter:
    def blocked(self) -> QuestionAnswerResult:
        return QuestionAnswerResult(
            status="blocked",
            message=blocked_answer_summary(),
            answer=ChatAnswer(summary=blocked_answer_summary()),
            material_ids=[],
            material_count=0,
            page_count=0,
            char_count=0,
        )

    def accepted(
        self, *, answer: ChatAnswer, selection: MaterialScopeSelection
    ) -> QuestionAnswerResult:
        return QuestionAnswerResult(
            status="accepted",
            message=answer.summary,
            answer=answer,
            material_ids=selection.ready_material_ids,
            material_count=len(selection.ready_materials),
            page_count=selection.page_count,
            char_count=selection.char_count,
        )


def blocked_answer_summary() -> str:
    return "읽기 완료된 자료가 없어 답할 수 없습니다."
