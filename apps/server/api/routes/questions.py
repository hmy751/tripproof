from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from server.api.deps import (
    get_library_chat_answer_composer,
    get_material_store,
    get_question_observation_sink,
    get_runtime_config_settings,
)
from server.answers.library_chat import LibraryChatAnswerComposer
from server.materials.store import MaterialStore
from server.questions.observation import QuestionObservationSink
from server.runtime.config_snapshot import RuntimeConfigSettings
from server.schemas.questions import QuestionRequest, QuestionResponse
from server.use_cases.questions import AskQuestionCommand, AskQuestionUseCase, EmptyQuestionError

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionResponse)
def ask_question(
    payload: QuestionRequest,
    store: Annotated[MaterialStore, Depends(get_material_store)],
    answer_composer: Annotated[LibraryChatAnswerComposer, Depends(get_library_chat_answer_composer)],
    observation_sink: Annotated[QuestionObservationSink, Depends(get_question_observation_sink)],
    runtime_config: Annotated[RuntimeConfigSettings, Depends(get_runtime_config_settings)],
) -> QuestionResponse:
    use_case = AskQuestionUseCase(
        store=store,
        answer_composer=answer_composer,
        observation_sink=observation_sink,
        runtime_config=runtime_config,
    )
    try:
        result = use_case.run(
            AskQuestionCommand(question=payload.question, material_ids=payload.material_ids)
        )
    except EmptyQuestionError as error:
        raise HTTPException(status_code=400, detail="질문을 입력해야 합니다.") from error
    return result.response
