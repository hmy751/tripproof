from __future__ import annotations

from server.retrieval.embeddings import EmbeddingProfile
from server.retrieval.models import EmbeddingRecord, SourceUnit
from server.retrieval.repository import RetrievalRecords, VectorSourceUnitMatch
from server.retrieval.search import retrieve_context, retrieve_context_with_trace


def test_retrieve_context_prefers_vector_similarity_over_lexical_matches() -> None:
    relevant = _source_unit(
        id="su_relevant",
        text="입실은 오후 세 시부터 가능합니다.",
    )
    lexical_decoy = _source_unit(
        id="su_decoy",
        text="check-in time check-in time check-in time이라는 단어가 반복되지만 실제 시간 안내는 없습니다.",
    )
    provider = FakeEmbeddingProvider(query_vector=[1.0, 0.0])
    embeddings = [
        _embedding_record(source_unit_id=relevant.id, vector=[1.0, 0.0]),
        _embedding_record(source_unit_id=lexical_decoy.id, vector=[0.2, 0.98]),
    ]

    context = retrieve_context(
        target_id="checkin_start_time",
        query="check-in time?",
        source_units=[lexical_decoy, relevant],
        embedding_records=embeddings,
        embedding_provider=provider,
    )

    assert [candidate.source_unit.id for candidate in context.candidates] == [
        "su_relevant",
        "su_decoy",
    ]
    assert context.candidates[0].vector_score == 1.0
    assert context.candidates[0].lexical_score == 0
    assert context.candidates[1].lexical_score > context.candidates[0].lexical_score


def test_retrieve_context_uses_lexical_search_when_vectors_are_not_ready() -> None:
    relevant = _source_unit(
        id="su_relevant",
        text="체크인 시 예약 확정서를 제시해 주세요.",
    )
    unrelated = _source_unit(
        id="su_unrelated",
        text="조식은 2층 레스토랑에서 제공됩니다.",
    )

    context = retrieve_context(
        target_id="booking_confirmation",
        query="예약 확정서 제시",
        source_units=[unrelated, relevant],
        embedding_records=[],
    )

    assert [candidate.source_unit.id for candidate in context.candidates] == [
        "su_relevant"
    ]
    assert context.candidates[0].vector_score is None
    assert context.candidates[0].lexical_score > 0


def test_lexical_search_does_not_let_repeated_terms_hide_earlier_relevant_source_unit() -> (
    None
):
    arrival = _source_unit(
        id="su_arrival",
        text="Arrival : 체크인 : 2025년 3월 09일 Departure : 체크아웃 : 2025년 3월 13일",
    )
    cancellation = _source_unit(
        id="su_cancellation",
        text=(
            "체크인 날짜 전 1일 이내 예약 취소 시 취소 요금이 부과됩니다. "
            "체크인하지 않을 경우 노쇼로 간주됩니다. 익스프레스 체크인."
        ),
    )

    context = retrieve_context(
        target_id="library_chat_answer",
        query="체크인 날짜가 어떻게 돼?",
        source_units=[arrival, cancellation],
        embedding_records=[],
    )

    assert [candidate.source_unit.id for candidate in context.candidates] == [
        "su_arrival",
        "su_cancellation",
    ]


def test_retrieve_context_uses_repository_vector_match_when_available() -> None:
    source_unit = _source_unit(
        id="su_supabase",
        text="Supabase vector search가 선택한 source unit입니다.",
    )
    embedding = _embedding_record(source_unit_id=source_unit.id, vector=[1.0, 0.0])
    repository = FakeRetrievalRepository(
        match=VectorSourceUnitMatch(
            source_unit=source_unit,
            embedding_record=embedding,
            similarity=0.91,
        )
    )
    provider = FakeEmbeddingProvider(query_vector=[1.0, 0.0])

    context = retrieve_context(
        target_id="checkin_start_time",
        query="check-in time?",
        source_units=[],
        embedding_records=[embedding],
        embedding_provider=provider,
        retrieval_repository=repository,
        material_ids=["mat_1"],
    )

    assert [candidate.source_unit.id for candidate in context.candidates] == [
        "su_supabase"
    ]
    assert context.candidates[0].score == 0.91
    assert repository.seen_material_ids == ["mat_1"]
    assert repository.seen_query_embedding == [1.0, 0.0]


def test_retrieve_context_with_trace_records_repository_vector_strategy() -> None:
    source_unit = _source_unit(
        id="su_supabase",
        text="Supabase vector search가 선택한 source unit입니다.",
    )
    embedding = _embedding_record(source_unit_id=source_unit.id, vector=[1.0, 0.0])
    repository = FakeRetrievalRepository(
        match=VectorSourceUnitMatch(
            source_unit=source_unit,
            embedding_record=embedding,
            similarity=0.91,
        )
    )
    provider = FakeEmbeddingProvider(query_vector=[1.0, 0.0])

    retrieved = retrieve_context_with_trace(
        target_id="checkin_start_time",
        query="check-in time?",
        source_units=[],
        embedding_records=[embedding],
        embedding_provider=provider,
        retrieval_repository=repository,
        material_ids=["mat_1"],
    )

    assert [candidate.source_unit.id for candidate in retrieved.context.candidates] == [
        "su_supabase"
    ]
    assert retrieved.source_retrieval.strategy == "repository_vector"
    assert retrieved.source_retrieval.query_embedding_attempted is True
    assert retrieved.source_retrieval.query_embedding_available is True
    assert retrieved.source_retrieval.vector_attempted is True
    assert retrieved.source_retrieval.vector_candidate_count == 1
    assert retrieved.source_retrieval.fallback_used is False


def test_retrieve_context_falls_back_to_lexical_when_repository_vector_match_is_empty() -> (
    None
):
    source_unit = _source_unit(
        id="su_lexical",
        text="체크인 시 예약 확정서를 제시해 주세요.",
    )
    embedding = _embedding_record(source_unit_id=source_unit.id, vector=[1.0, 0.0])
    repository = EmptyRetrievalRepository()
    provider = FakeEmbeddingProvider(query_vector=[1.0, 0.0])

    context = retrieve_context(
        target_id="booking_confirmation",
        query="예약 확정서 제시",
        source_units=[source_unit],
        embedding_records=[embedding],
        embedding_provider=provider,
        retrieval_repository=repository,
        material_ids=["mat_1"],
    )

    assert [candidate.source_unit.id for candidate in context.candidates] == [
        "su_lexical"
    ]
    assert context.candidates[0].vector_score == 1.0
    assert context.candidates[0].lexical_score > 0


def test_retrieve_context_with_trace_records_repository_fallback_to_local_vector() -> (
    None
):
    source_unit = _source_unit(
        id="su_local_vector",
        text="체크인 시 예약 확정서를 제시해 주세요.",
    )
    embedding = _embedding_record(source_unit_id=source_unit.id, vector=[1.0, 0.0])
    repository = EmptyRetrievalRepository()
    provider = FakeEmbeddingProvider(query_vector=[1.0, 0.0])

    retrieved = retrieve_context_with_trace(
        target_id="booking_confirmation",
        query="예약 확정서 제시",
        source_units=[source_unit],
        embedding_records=[embedding],
        embedding_provider=provider,
        retrieval_repository=repository,
        material_ids=["mat_1"],
    )

    assert [candidate.source_unit.id for candidate in retrieved.context.candidates] == [
        "su_local_vector"
    ]
    assert retrieved.source_retrieval.strategy == "local_vector"
    assert retrieved.source_retrieval.query_embedding_attempted is True
    assert retrieved.source_retrieval.query_embedding_available is True
    assert retrieved.source_retrieval.vector_attempted is True
    assert retrieved.source_retrieval.vector_candidate_count == 1
    assert retrieved.source_retrieval.fallback_used is True


def test_retrieve_context_with_trace_records_lexical_strategy_without_query_embedding() -> (
    None
):
    source_unit = _source_unit(
        id="su_lexical",
        text="체크인 시 예약 확정서를 제시해 주세요.",
    )

    retrieved = retrieve_context_with_trace(
        target_id="booking_confirmation",
        query="예약 확정서 제시",
        source_units=[source_unit],
        embedding_records=[],
    )

    assert [candidate.source_unit.id for candidate in retrieved.context.candidates] == [
        "su_lexical"
    ]
    assert retrieved.source_retrieval.strategy == "lexical"
    assert retrieved.source_retrieval.query_embedding_attempted is False
    assert retrieved.source_retrieval.query_embedding_available is False
    assert retrieved.source_retrieval.vector_attempted is False
    assert retrieved.source_retrieval.vector_candidate_count == 0
    assert retrieved.source_retrieval.fallback_used is False


def _source_unit(*, id: str, text: str) -> SourceUnit:
    return SourceUnit(
        id=id,
        material_id="mat_1",
        file_name="booking.pdf",
        page=1,
        unit_index=1,
        locator=f"booking.pdf {id}",
        text=text,
        search_text=text,
        start=0,
        end=len(text),
    )


def _embedding_record(*, source_unit_id: str, vector: list[float]) -> EmbeddingRecord:
    return EmbeddingRecord(
        id=f"emb_{source_unit_id}",
        source_unit_id=source_unit_id,
        provider="fake",
        model="fake-embedding",
        dimensions=len(vector),
        vector=vector,
        status="ready",
    )


class FakeEmbeddingProvider:
    def __init__(self, *, query_vector: list[float]) -> None:
        self.profile = EmbeddingProfile(
            provider="fake",
            model="fake-embedding",
            dimensions=len(query_vector),
        )
        self._query_vector = query_vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0 for _value in self._query_vector] for _text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._query_vector


class FakeRetrievalRepository:
    def __init__(self, *, match: VectorSourceUnitMatch) -> None:
        self._match = match
        self.seen_material_ids: list[str] = []
        self.seen_query_embedding: list[float] | None = None

    def upsert_material_records(
        self, *, material_id: str, records: RetrievalRecords
    ) -> None:
        raise AssertionError("not used")

    def records_for_materials(self, material_ids):
        raise AssertionError("not used")

    def match_source_units(
        self, *, material_ids, query_embedding, limit, similarity_threshold
    ):
        self.seen_material_ids = list(material_ids)
        self.seen_query_embedding = query_embedding
        return [self._match]

    def clear(self) -> None:
        raise AssertionError("not used")


class EmptyRetrievalRepository:
    def upsert_material_records(
        self, *, material_id: str, records: RetrievalRecords
    ) -> None:
        raise AssertionError("not used")

    def records_for_materials(self, material_ids):
        raise AssertionError("not used")

    def match_source_units(
        self, *, material_ids, query_embedding, limit, similarity_threshold
    ):
        return []

    def clear(self) -> None:
        raise AssertionError("not used")
