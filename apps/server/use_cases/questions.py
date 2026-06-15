from __future__ import annotations

from dataclasses import dataclass

from server.answers.library_chat import LibraryChatAnswerComposer
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
from server.questions.models import QuestionAnswerResult, QuestionStatus
from server.use_cases.question_responses import QuestionAnswerPresenter
from server.use_cases.question_retrieval import QuestionContextRetriever
from server.use_cases.question_scope import MaterialScopeSelector


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
    response: QuestionAnswerResult
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
        self._material_scope_selector = MaterialScopeSelector(store)
        self._context_retriever = QuestionContextRetriever(
            store=store, runtime_config=runtime_config
        )
        self._presenter = QuestionAnswerPresenter()

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

        selection = self._material_scope_selector.select(command.material_ids)
        ready_material_ids = selection.ready_material_ids
        if selection.is_empty:
            reporter.ready_materials_missing()
            reporter.emit()
            response = self._presenter.blocked()
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

        reporter.ready_materials_selected(ready_material_ids=ready_material_ids)

        try:
            retrieval_records = self._context_retriever.load_records(
                command.material_ids
            )
        except Exception:
            reporter.retrieval_records_failed()
            reporter.emit()
            raise
        reporter.retrieval_records_loaded(
            source_unit_count=len(retrieval_records.source_units),
            embedding_record_count=len(retrieval_records.embedding_records),
        )

        try:
            retrieved_context = self._context_retriever.retrieve(
                question=question_text,
                ready_material_ids=ready_material_ids,
                retrieval_records=retrieval_records,
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

        response = self._presenter.accepted(answer=answer, selection=selection)
        reporter.question_accepted()
        reporter.emit()
        return AskQuestionResult(
            response=response,
            trace=AskQuestionTrace(
                question_length=len(question_text),
                ready_material_ids=ready_material_ids,
                page_count=selection.page_count,
                char_count=selection.char_count,
                source_unit_count=len(retrieval_records.source_units),
                embedding_record_count=len(retrieval_records.embedding_records),
                retrieval_strategy=retrieved_context.source_retrieval.strategy,
                candidate_count=len(answer_context.candidates),
                answer_item_count=len(answer.items),
                final_status="accepted",
            ),
        )
