from __future__ import annotations

import pytest

from server.extraction.models import EvidenceState
from server.materials.store import MaterialStore
from server.questions.observation import InMemoryQuestionObservationSink
from server.retrieval.repository import InMemoryRetrievalRepository, RetrievalRecords
from server.runtime.config_snapshot import RuntimeConfigSettings
from server.schemas.answers import ChatAnswerItemResponse, ChatAnswerResponse
from server.use_cases.questions import AskQuestionCommand, AskQuestionUseCase


def test_ask_question_use_case_returns_accepted_trace_without_http_adapter() -> None:
    sink = InMemoryQuestionObservationSink()
    store = MaterialStore(retrieval_backend="memory")
    material = store.add_ready(
        name="Booking",
        file_name="booking.pdf",
        content_type="application/pdf",
        page_count=1,
        text="Hotel address is Hakata. Check-in starts at 15:00.",
        preview="Hotel address is Hakata.",
    )
    composer = SpyAnswerComposer()
    use_case = AskQuestionUseCase(
        store=store,
        answer_composer=composer,
        observation_sink=sink,
        runtime_config=_runtime_config(store),
    )

    result = use_case.run(
        AskQuestionCommand(question="  check-in time?  ", material_ids=[material.id])
    )

    assert result.response.status == "accepted"
    assert result.response.material_ids == [material.id]
    assert composer.last_question == "check-in time?"
    assert composer.last_context is not None
    assert composer.last_context.target_id == "library_chat_answer"
    assert result.trace.question_length == len("check-in time?")
    assert result.trace.ready_material_ids == [material.id]
    assert result.trace.page_count == 1
    assert result.trace.char_count == len("Hotel address is Hakata. Check-in starts at 15:00.")
    assert result.trace.source_unit_count == 1
    assert result.trace.embedding_record_count == 1
    assert result.trace.retrieval_strategy == "lexical"
    assert result.trace.candidate_count == 1
    assert result.trace.answer_item_count == 1
    assert result.trace.final_status == "accepted"
    assert result.trace.failure_kind is None

    record = sink.records[0]
    assert record.step("query_snapshot").facts == {"question_length": len("check-in time?")}
    assert record.step("retrieval_pipeline").status == "succeeded"
    assert record.step("answer_pipeline").status == "succeeded"
    assert record.final_question_status == "accepted"


def test_ask_question_use_case_returns_blocked_trace_without_ready_materials() -> None:
    sink = InMemoryQuestionObservationSink()
    store = MaterialStore(retrieval_backend="memory")
    use_case = AskQuestionUseCase(
        store=store,
        answer_composer=SpyAnswerComposer(),
        observation_sink=sink,
        runtime_config=_runtime_config(store),
    )

    result = use_case.run(AskQuestionCommand(question="check-in time?", material_ids=None))

    assert result.response.status == "blocked"
    assert result.response.material_count == 0
    assert result.trace.final_status == "blocked"
    assert result.trace.failure_kind == "no_ready_materials"
    record = sink.records[0]
    assert record.step("ready_material_selection").status == "failed"
    assert record.step("retrieval_pipeline").status == "not_started"
    assert record.final_question_status == "blocked"


def test_ask_question_use_case_records_retrieval_failure_without_http_adapter() -> None:
    sink = InMemoryQuestionObservationSink()
    store = MaterialStore(retrieval_repository=FailingReadRetrievalRepository())
    material = store.add_ready(
        name="Booking",
        file_name="booking.pdf",
        content_type="application/pdf",
        page_count=1,
        text="Check-in starts at 15:00.",
        preview="Check-in starts at 15:00.",
    )
    use_case = AskQuestionUseCase(
        store=store,
        answer_composer=SpyAnswerComposer(),
        observation_sink=sink,
        runtime_config=_runtime_config(store),
    )

    with pytest.raises(RuntimeError, match="retrieval records read failed"):
        use_case.run(AskQuestionCommand(question="check-in time?", material_ids=[material.id]))

    record = sink.records[0]
    assert record.step("query_snapshot").status == "succeeded"
    assert record.step("ready_material_selection").status == "succeeded"
    assert record.step("retrieval_record_load").status == "failed"
    assert record.step("retrieval_record_load").failure_kind == "retrieval_failed"
    assert record.step("retrieval_pipeline").status == "not_started"
    assert record.final_question_status is None
    assert record.failure_kind == "retrieval_failed"


class SpyAnswerComposer:
    def __init__(self) -> None:
        self.last_question = None
        self.last_context = None

    def compose(self, *, question, context):
        self.last_question = question
        self.last_context = context
        return ChatAnswerResponse(
            summary="composer contract reached",
            items=[
                ChatAnswerItemResponse(
                    id="answer",
                    label="답변",
                    body="use case called LibraryChatAnswerComposer.compose",
                    evidence_state=EvidenceState.MISSING,
                    value=None,
                    evidence=[],
                )
            ],
        )


class FailingReadRetrievalRepository:
    def __init__(self) -> None:
        self._delegate = InMemoryRetrievalRepository()

    def upsert_material_records(self, *, material_id: str, records: RetrievalRecords) -> None:
        self._delegate.upsert_material_records(material_id=material_id, records=records)

    def records_for_materials(self, material_ids):
        raise RuntimeError("retrieval records read failed")

    def match_source_units(self, *, material_ids, query_embedding, limit, similarity_threshold):
        return []

    def clear(self) -> None:
        self._delegate.clear()


def _runtime_config(store: MaterialStore) -> RuntimeConfigSettings:
    return RuntimeConfigSettings(
        retrieval_backend=store.retrieval_backend,
        retrieval_top_k=3,
        retrieval_similarity_threshold=0.0,
        embedding_auto_generate=store.embedding_auto_generate,
        embedding_profile=store.embedding_profile,
    )
