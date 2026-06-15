from __future__ import annotations

from dataclasses import dataclass

from server.answers.library_chat import (
    LIBRARY_CHAT_TARGET_ID,
    LibraryChatAnswerComposer,
)
from server.materials.store import MaterialStore
from server.questions.observation import (
    QuestionObservationFailureKind,
    QuestionObservationReporter,
    QuestionObservationSink,
)
from server.retrieval.search import SourceRetrievalStrategy, retrieve_context_with_trace
from server.runtime.config_snapshot import (
    RuntimeConfigSettings,
    answer_model_runtime_config_snapshot_from_composer,
    prompt_runtime_config_snapshot_from_composer,
    runtime_config_snapshot_from_settings,
)
from server.schemas.answers import ChatAnswerResponse
from server.schemas.questions import QuestionResponse, QuestionStatus


@dataclass(frozen=True)
class AskQuestionCommand:
    question: str
    material_ids: list[str] | None


@dataclass(frozen=True)
class AskQuestionTrace:
    question_length: int
    ready_material_ids: list[str]
    page_count: int
    char_count: int
    source_unit_count: int | None = None
    embedding_record_count: int | None = None
    retrieval_strategy: SourceRetrievalStrategy | None = None
    candidate_count: int | None = None
    answer_item_count: int | None = None
    final_status: QuestionStatus | None = None
    failure_kind: QuestionObservationFailureKind | None = None


@dataclass(frozen=True)
class AskQuestionResult:
    response: QuestionResponse
    trace: AskQuestionTrace


class EmptyQuestionError(ValueError):
    def __init__(self, trace: AskQuestionTrace) -> None:
        super().__init__("Question text is empty.")
        self.trace = trace


class AskQuestionUseCase:
    def __init__(
        self,
        *,
        store: MaterialStore,
        answer_composer: LibraryChatAnswerComposer,
        observation_sink: QuestionObservationSink,
        runtime_config: RuntimeConfigSettings,
    ) -> None:
        self._store = store
        self._answer_composer = answer_composer
        self._observation_sink = observation_sink
        self._runtime_config = runtime_config

    def run(self, command: AskQuestionCommand) -> AskQuestionResult:
        prompt_snapshot = prompt_runtime_config_snapshot_from_composer(
            self._answer_composer
        )
        reporter = QuestionObservationReporter(
            sink=self._observation_sink,
            runtime_config_snapshot=runtime_config_snapshot_from_settings(
                self._runtime_config,
                prompt=prompt_snapshot,
                answer_model=answer_model_runtime_config_snapshot_from_composer(
                    self._answer_composer
                ),
            ),
        )

        question_text = command.question.strip()
        if not question_text:
            trace = AskQuestionTrace(
                question_length=0,
                ready_material_ids=[],
                page_count=0,
                char_count=0,
                failure_kind="empty_question",
            )
            reporter.query_empty()
            reporter.emit()
            raise EmptyQuestionError(trace)
        reporter.query_succeeded(question_text)

        ready_materials = self._store.ready_materials(command.material_ids)
        ready_material_ids = [material.id for material in ready_materials]
        if not ready_materials:
            reporter.ready_materials_missing()
            reporter.emit()
            response = QuestionResponse(
                status="blocked",
                message=_blocked_answer_summary(),
                answer=ChatAnswerResponse(summary=_blocked_answer_summary()),
                material_ids=[],
                material_count=0,
                page_count=0,
                char_count=0,
            )
            return AskQuestionResult(
                response=response,
                trace=AskQuestionTrace(
                    question_length=len(question_text),
                    ready_material_ids=[],
                    page_count=0,
                    char_count=0,
                    final_status="blocked",
                    failure_kind="no_ready_materials",
                ),
            )

        page_count = sum(material.page_count for material in ready_materials)
        char_count = sum(len(material.text) for material in ready_materials)
        reporter.ready_materials_selected(ready_material_ids=ready_material_ids)

        try:
            retrieval_records = self._store.retrieval_records(command.material_ids)
        except Exception:
            reporter.retrieval_records_failed()
            reporter.emit()
            raise
        reporter.retrieval_records_loaded(
            source_unit_count=len(retrieval_records.source_units),
            embedding_record_count=len(retrieval_records.embedding_records),
        )

        try:
            retrieved_context = retrieve_context_with_trace(
                target_id=LIBRARY_CHAT_TARGET_ID,
                query=question_text,
                source_units=retrieval_records.source_units,
                embedding_records=retrieval_records.embedding_records,
                embedding_provider=self._store.embedding_provider,
                retrieval_repository=self._store.retrieval_repository,
                material_ids=ready_material_ids,
                top_k=self._runtime_config.retrieval_top_k,
                similarity_threshold=self._runtime_config.retrieval_similarity_threshold,
            )
        except Exception:
            reporter.source_retrieval_failed()
            reporter.emit()
            raise

        answer_context = retrieved_context.context
        reporter.source_context_retrieved(
            source_retrieval=retrieved_context.source_retrieval,
            answer_context=answer_context,
        )
        reporter.prompt_snapshotted(prompt_snapshot)

        try:
            answer = self._answer_composer.compose(
                question=question_text, context=answer_context
            )
        except Exception:
            reporter.answer_composer_failed()
            reporter.emit()
            raise
        reporter.answer_composed(answer)

        response = QuestionResponse(
            status="accepted",
            message=answer.summary,
            answer=answer,
            material_ids=ready_material_ids,
            material_count=len(ready_materials),
            page_count=page_count,
            char_count=char_count,
        )
        reporter.question_accepted()
        reporter.emit()
        return AskQuestionResult(
            response=response,
            trace=AskQuestionTrace(
                question_length=len(question_text),
                ready_material_ids=ready_material_ids,
                page_count=page_count,
                char_count=char_count,
                source_unit_count=len(retrieval_records.source_units),
                embedding_record_count=len(retrieval_records.embedding_records),
                retrieval_strategy=retrieved_context.source_retrieval.strategy,
                candidate_count=len(answer_context.candidates),
                answer_item_count=len(answer.items),
                final_status="accepted",
            ),
        )


def _blocked_answer_summary() -> str:
    return "읽기 완료된 자료가 없어 답할 수 없습니다."
