from __future__ import annotations

from server.answers.library_chat import LIBRARY_CHAT_TARGET_ID
from server.materials.store import MaterialStore
from server.retrieval.repository import RetrievalRecords
from server.retrieval.search import RetrievedContext, retrieve_context_with_trace
from server.runtime.config_snapshot import RuntimeConfigSettings


class QuestionContextRetriever:
    def __init__(
        self, *, store: MaterialStore, runtime_config: RuntimeConfigSettings
    ) -> None:
        self._store = store
        self._runtime_config = runtime_config

    def load_records(self, material_ids: list[str] | None) -> RetrievalRecords:
        return self._store.retrieval_records(material_ids)

    def retrieve(
        self,
        *,
        question: str,
        ready_material_ids: list[str],
        retrieval_records: RetrievalRecords,
    ) -> RetrievedContext:
        return retrieve_context_with_trace(
            target_id=LIBRARY_CHAT_TARGET_ID,
            query=question,
            source_units=retrieval_records.source_units,
            embedding_records=retrieval_records.embedding_records,
            embedding_provider=self._store.embedding_provider,
            retrieval_repository=self._store.retrieval_repository,
            material_ids=ready_material_ids,
            top_k=self._runtime_config.retrieval_top_k,
            similarity_threshold=self._runtime_config.retrieval_similarity_threshold,
        )
