from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from server.api.deps import (
    get_library_chat_answer_composer,
    get_material_store,
    get_question_observation_sink,
    get_runtime_config_settings,
)
from server.answers.library_chat import LIBRARY_CHAT_TARGET_ID, LibraryChatAnswerComposer
from server.materials.store import MaterialStore
from server.questions.observation import (
    QuestionObservationRecorder,
    QuestionObservationSink,
    answer_projection_facts,
    emit_question_observation,
    prompt_snapshot_facts,
    retrieval_candidate_facts,
    source_retrieval_facts,
)
from server.retrieval.search import retrieve_context_with_trace
from server.runtime.config_snapshot import (
    RuntimeConfigSettings,
    answer_model_runtime_config_snapshot_from_composer,
    prompt_runtime_config_snapshot_from_composer,
    runtime_config_snapshot_from_settings,
)
from server.schemas.answers import ChatAnswerResponse
from server.schemas.questions import QuestionRequest, QuestionResponse

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionResponse)
def ask_question(
    payload: QuestionRequest,
    store: Annotated[MaterialStore, Depends(get_material_store)],
    answer_composer: Annotated[LibraryChatAnswerComposer, Depends(get_library_chat_answer_composer)],
    observation_sink: Annotated[QuestionObservationSink, Depends(get_question_observation_sink)],
    runtime_config: Annotated[RuntimeConfigSettings, Depends(get_runtime_config_settings)],
) -> QuestionResponse:
    prompt_snapshot = prompt_runtime_config_snapshot_from_composer(answer_composer)
    observation = QuestionObservationRecorder(
        runtime_config_snapshot=runtime_config_snapshot_from_settings(
            runtime_config,
            prompt=prompt_snapshot,
            answer_model=answer_model_runtime_config_snapshot_from_composer(answer_composer),
        )
    )
    question = payload.question.strip()
    if not question:
        observation.fail("query_snapshot", "empty_question", facts={"question_length": 0})
        observation.finalize(None, failure_kind="empty_question")
        emit_question_observation(sink=observation_sink, recorder=observation)
        raise HTTPException(status_code=400, detail="질문을 입력해야 합니다.")
    observation.succeed("query_snapshot", facts={"question_length": len(question)})

    ready_materials = store.ready_materials(payload.material_ids)
    ready_material_ids = [material.id for material in ready_materials]
    if not ready_materials:
        observation.fail(
            "ready_material_selection",
            "no_ready_materials",
            facts={"ready_material_count": 0, "ready_material_ids": []},
        )
        observation.succeed("question_status", facts={"status": "blocked"})
        observation.finalize("blocked", failure_kind="no_ready_materials")
        response = QuestionResponse(
            status="blocked",
            message="읽기 완료된 자료가 없어 답할 수 없습니다.",
            answer=ChatAnswerResponse(summary="읽기 완료된 자료가 없어 답할 수 없습니다."),
            material_ids=[],
            material_count=0,
            page_count=0,
            char_count=0,
        )
        emit_question_observation(sink=observation_sink, recorder=observation)
        return response

    page_count = sum(material.page_count for material in ready_materials)
    char_count = sum(len(material.text) for material in ready_materials)
    observation.succeed(
        "ready_material_selection",
        facts={
            "ready_material_count": len(ready_materials),
            "ready_material_ids": ready_material_ids,
        },
    )

    try:
        retrieval_records = store.retrieval_records(payload.material_ids)
    except Exception:
        observation.fail("retrieval_record_load", "retrieval_failed", facts={"executed": True})
        observation.finalize(None, failure_kind="retrieval_failed")
        emit_question_observation(sink=observation_sink, recorder=observation)
        raise
    observation.succeed(
        "retrieval_record_load",
        facts={
            "executed": True,
            "source_unit_count": len(retrieval_records.source_units),
            "embedding_record_count": len(retrieval_records.embedding_records),
        },
    )

    try:
        retrieved_context = retrieve_context_with_trace(
            target_id=LIBRARY_CHAT_TARGET_ID,
            query=question,
            source_units=retrieval_records.source_units,
            embedding_records=retrieval_records.embedding_records,
            embedding_provider=store.embedding_provider,
            retrieval_repository=store.retrieval_repository,
            material_ids=ready_material_ids,
            top_k=runtime_config.retrieval_top_k,
            similarity_threshold=runtime_config.retrieval_similarity_threshold,
        )
    except Exception:
        observation.fail("source_retrieval", "retrieval_failed", facts={"executed": True})
        observation.finalize(None, failure_kind="retrieval_failed")
        emit_question_observation(sink=observation_sink, recorder=observation)
        raise
    context = retrieved_context.context
    observation.succeed("source_retrieval", facts=source_retrieval_facts(retrieved_context.source_retrieval))
    observation.succeed("context_assembly", facts={"executed": True, "target_id": LIBRARY_CHAT_TARGET_ID})
    observation.succeed("candidate_summary", facts=retrieval_candidate_facts(context))

    observation.succeed("prompt_snapshot", facts=prompt_snapshot_facts(prompt_snapshot))

    try:
        answer = answer_composer.compose(question=question, context=context)
    except Exception:
        observation.fail("composer_call", "answer_composer_failed")
        observation.finalize(None, failure_kind="answer_composer_failed")
        emit_question_observation(sink=observation_sink, recorder=observation)
        raise
    observation.succeed("composer_call", facts={"result": "succeeded"})
    observation.succeed("answer_projection", facts=answer_projection_facts(answer))

    response = QuestionResponse(
        status="accepted",
        message=answer.summary,
        answer=answer,
        material_ids=ready_material_ids,
        material_count=len(ready_materials),
        page_count=page_count,
        char_count=char_count,
    )
    observation.succeed("question_status", facts={"status": "accepted"})
    observation.finalize("accepted")
    emit_question_observation(sink=observation_sink, recorder=observation)
    return response
