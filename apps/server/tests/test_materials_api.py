from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import server.app as server_app
import server.api.routes.materials as materials_route
from server.app import create_app
from server.extraction.models import EvidenceRef, EvidenceState
from server.materials.observation import InMemoryMaterialUploadObservationSink
from server.materials.store import MaterialStore
from server.retrieval.embeddings import EmbeddingProfile
from server.retrieval.repository import InMemoryRetrievalRepository, RetrievalRecords
from server.schemas.answers import ChatAnswerItemResponse, ChatAnswerResponse
from server.schemas.facts import EvidenceRefResponse


def test_upload_text_pdf_returns_ready_material() -> None:
    observation_sink = InMemoryMaterialUploadObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            material_upload_observation_sink=observation_sink,
        )
    )

    response = client.post(
        "/api/materials",
        data={"displayName": "Agoda Fukuoka"},
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00"), "application/pdf")},
    )

    assert response.status_code == 200
    material = response.json()
    assert material["status"] == "ready"
    assert material["name"] == "Agoda Fukuoka"
    assert material["fileName"] == "booking.pdf"
    assert material["pageCount"] == 1
    assert "Check-in starts at 15:00" in material["preview"]
    assert "observation" not in material
    assert "debug" not in material
    assert "raw" not in material

    records = observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.operation == "material_upload"
    assert record.material_id == material["id"]
    assert _step_names(record) == [
        "upload",
        "pdf_parse",
        "source_unit_build",
        "embedding_record_build",
        "retrieval_repository_upsert",
    ]
    assert record.step("upload").status == "succeeded"
    assert record.step("upload").facts["file_name"] == "booking.pdf"
    assert record.step("upload").facts["content_type"] == "application/pdf"
    assert record.step("upload").facts["size_bytes"] > 0
    assert record.step("pdf_parse").status == "succeeded"
    assert record.step("pdf_parse").facts == {"page_count": 1}
    assert record.step("source_unit_build").status == "succeeded"
    assert record.step("source_unit_build").facts == {"count": 1}
    assert record.step("embedding_record_build").status == "succeeded"
    assert record.step("embedding_record_build").facts == {
        "count": 1,
        "status_counts": {"pending": 1},
    }
    assert record.step("retrieval_repository_upsert").status == "succeeded"
    assert record.final_material_status == "ready"
    assert record.failure_kind is None


def test_upload_blank_pdf_returns_failed_material() -> None:
    observation_sink = InMemoryMaterialUploadObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            material_upload_observation_sink=observation_sink,
        )
    )

    response = client.post(
        "/api/materials",
        files={"file": ("blank.pdf", _blank_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    material = response.json()
    assert material["status"] == "failed"
    assert material["pageCount"] is None
    assert material["error"] == "텍스트를 추출할 수 없는 PDF입니다."
    assert "observation" not in material
    assert "debug" not in material
    assert "raw" not in material

    records = observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.material_id == material["id"]
    assert record.step("upload").status == "succeeded"
    assert record.step("pdf_parse").status == "failed"
    assert record.step("pdf_parse").failure_kind == "parse_failed"
    assert record.step("source_unit_build").status == "not_started"
    assert record.step("embedding_record_build").status == "not_started"
    assert record.step("retrieval_repository_upsert").status == "not_started"
    assert record.final_material_status == "failed"
    assert record.failure_kind == "parse_failed"


def test_upload_non_pdf_records_unsupported_file_observation() -> None:
    observation_sink = InMemoryMaterialUploadObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            material_upload_observation_sink=observation_sink,
        )
    )

    response = client.post(
        "/api/materials",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 200
    material = response.json()
    assert material["status"] == "failed"
    assert material["error"] == "PDF 파일만 지원합니다."
    assert "observation" not in material
    assert "debug" not in material
    assert "raw" not in material

    records = observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.material_id == material["id"]
    assert record.step("upload").facts["file_name"] == "notes.txt"
    assert record.step("upload").facts["content_type"] == "text/plain"
    assert record.step("upload").status == "failed"
    assert record.step("upload").failure_kind == "unsupported_file"
    assert record.step("pdf_parse").status == "not_started"
    assert record.final_material_status == "failed"
    assert record.failure_kind == "unsupported_file"


def test_upload_too_large_pdf_records_size_limit_observation(monkeypatch) -> None:
    observation_sink = InMemoryMaterialUploadObservationSink()
    monkeypatch.setattr(materials_route, "MAX_UPLOAD_BYTES", 5)
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            material_upload_observation_sink=observation_sink,
        )
    )

    response = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", b"%PDF-too-large", "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "PDF 파일이 너무 큽니다."}

    records = observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.material_id is None
    assert record.step("upload").facts["file_name"] == "booking.pdf"
    assert record.step("upload").facts["size_bytes"] == len(b"%PDF-too-large")
    assert record.step("upload").facts["size_limit_bytes"] == 5
    assert record.step("upload").status == "failed"
    assert record.step("upload").failure_kind == "size_limit_exceeded"
    assert record.step("pdf_parse").status == "not_started"
    assert record.final_material_status == "failed"
    assert record.failure_kind == "size_limit_exceeded"


def test_upload_observation_sink_failure_does_not_change_ready_response() -> None:
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            material_upload_observation_sink=FailingObservationSink(),
        )
    )

    response = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00"), "application/pdf")},
    )

    assert response.status_code == 200
    material = response.json()
    assert material["status"] == "ready"
    assert "observation" not in material
    assert "debug" not in material
    assert "raw" not in material


def test_question_returns_chat_answer_for_ready_materials() -> None:
    composer = FakeLibraryChatAnswerComposer(
        body="체크인 시작 시각은 15:00입니다.",
        snippet="Check-in starts at 15:00.",
    )
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=composer,
        )
    )
    upload = client.post(
        "/api/materials",
        files={
            "file": (
                "booking.pdf",
                _pdf_with_text("Hotel address is Hakata. Check-in starts at 15:00."),
                "application/pdf",
            )
        },
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["materialIds"] == [material_id]
    assert body["materialCount"] == 1
    assert body["pageCount"] == 1
    assert body["answer"]["summary"] == "자료에서 확인한 답변입니다."
    assert body["answer"]["items"][0]["id"] == "answer"
    assert body["answer"]["items"][0]["body"] == "체크인 시작 시각은 15:00입니다."
    assert body["answer"]["items"][0]["evidence"][0]["snippet"] == "Check-in starts at 15:00."
    assert composer.last_question == "check-in time?"
    assert composer.last_context is not None
    assert composer.last_context.query == "check-in time?"
    assert composer.last_context.candidates
    assert "excerpt" not in body
    assert "facts" not in body


def test_question_route_calls_library_chat_answer_composer_contract() -> None:
    composer = SpyLibraryChatAnswerComposer()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=composer,
        )
    )
    upload = client.post(
        "/api/materials",
        files={
            "file": (
                "booking.pdf",
                _pdf_with_text("Hotel address is Hakata. Check-in starts at 15:00."),
                "application/pdf",
            )
        },
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["answer"]["summary"] == "composer contract reached"
    assert body["answer"]["items"][0]["body"] == "route called LibraryChatAnswerComposer.compose"
    assert composer.calls == 1
    assert composer.last_question == "check-in time?"
    assert composer.last_context is not None
    assert composer.last_context.target_id == "library_chat_answer"
    assert [candidate.source_unit.text for candidate in composer.last_context.candidates] == [
        "Hotel address is Hakata. Check-in starts at 15:00."
    ]


def test_ready_material_builds_source_units_and_pending_embeddings() -> None:
    store = MaterialStore()

    material = store.add_ready(
        name="Agoda Fukuoka",
        file_name="booking.pdf",
        content_type="application/pdf",
        page_count=2,
        text="[page 1]\nShow your booking confirmation.\n\n[page 2]\nCheck-out is at 11:00.",
        preview="Show your booking confirmation.",
    )

    stored = store.ready_materials([material.id])[0]
    assert [unit.page for unit in stored.source_units] == [1, 2]
    assert stored.source_units[0].locator == "booking.pdf p.1 u.1"
    assert stored.source_units[0].text == "Show your booking confirmation."
    assert stored.source_units[0].search_text == "Show your booking confirmation."
    assert {record.status for record in stored.embedding_records} == {"pending"}
    assert {record.source_unit_id for record in stored.embedding_records} == {
        unit.id for unit in stored.source_units
    }


def test_material_store_can_generate_embedding_records_with_provider() -> None:
    provider = FakeEmbeddingProvider(dimensions=3)
    store = MaterialStore(embedding_provider=provider, embedding_auto_generate=True)

    material = store.add_ready(
        name="Agoda Fukuoka",
        file_name="booking.pdf",
        content_type="application/pdf",
        page_count=1,
        text="[page 1]\nShow your booking confirmation.",
        preview="Show your booking confirmation.",
    )

    stored = store.ready_materials([material.id])[0]
    assert len(stored.embedding_records) == 1
    embedding = stored.embedding_records[0]
    assert embedding.provider == "ollama"
    assert embedding.model == "nomic-embed-text-v2-moe"
    assert embedding.dimensions == 3
    assert embedding.status == "ready"
    assert embedding.vector == [1.0, 0.0, 0.0]


def test_material_store_does_not_publish_ready_material_when_retrieval_upsert_fails() -> None:
    store = MaterialStore(retrieval_repository=FailingRetrievalRepository())

    with pytest.raises(RuntimeError, match="upsert failed"):
        store.add_ready(
            name="Agoda Fukuoka",
            file_name="booking.pdf",
            content_type="application/pdf",
            page_count=1,
            text="Show your booking confirmation.",
            preview="Show your booking confirmation.",
        )

    assert store.list_public() == []


def test_upload_records_repository_upsert_failure_without_publishing_ready_material() -> None:
    observation_sink = InMemoryMaterialUploadObservationSink()
    store = MaterialStore(retrieval_repository=FailingRetrievalRepository())
    client = TestClient(
        create_app(store=store, material_upload_observation_sink=observation_sink),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Show your booking confirmation."), "application/pdf")},
    )

    assert response.status_code == 500
    assert store.list_public() == []

    records = observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.material_id is not None
    assert record.step("upload").status == "succeeded"
    assert record.step("pdf_parse").status == "succeeded"
    assert record.step("source_unit_build").status == "succeeded"
    assert record.step("source_unit_build").facts == {"count": 1}
    assert record.step("embedding_record_build").status == "succeeded"
    assert record.step("embedding_record_build").facts == {
        "count": 1,
        "status_counts": {"pending": 1},
    }
    assert record.step("retrieval_repository_upsert").status == "failed"
    assert record.step("retrieval_repository_upsert").failure_kind == "repository_upsert_failed"
    assert record.final_material_status == "failed"
    assert record.failure_kind == "repository_upsert_failed"


def test_question_blocks_when_only_failed_material_exists() -> None:
    client = TestClient(create_app(embedding_auto_generate=False, retrieval_backend="memory"))
    client.post(
        "/api/materials",
        files={"file": ("blank.pdf", _blank_pdf(), "application/pdf")},
    )

    response = client.post("/api/questions", json={"question": "check-in time?"})

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["materialCount"] == 0


def test_create_app_uses_supabase_repository_when_backend_enabled(monkeypatch) -> None:
    repository = InMemoryRetrievalRepository()
    monkeypatch.setattr(server_app, "RETRIEVAL_BACKEND", "supabase")
    monkeypatch.setattr(server_app, "create_supabase_retrieval_repository_from_config", lambda: repository)

    app = server_app.create_app(embedding_auto_generate=False)

    assert app.state.material_store.retrieval_repository is repository


def test_create_app_uses_provided_store_without_building_supabase_repository(monkeypatch) -> None:
    store = MaterialStore()
    monkeypatch.setattr(server_app, "RETRIEVAL_BACKEND", "supabase")

    def fail_if_called():
        raise AssertionError("Supabase repository should not be created when store is provided.")

    monkeypatch.setattr(server_app, "create_supabase_retrieval_repository_from_config", fail_if_called)

    app = server_app.create_app(store=store)

    assert app.state.material_store is store


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _pdf_with_text(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("utf-8"))
    page[NameObject("/Contents")] = stream
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _step_names(record) -> list[str]:
    return [step.name for step in record.steps]


class FakeEmbeddingProvider:
    def __init__(self, *, dimensions: int) -> None:
        self.profile = EmbeddingProfile(
            provider="ollama",
            model="nomic-embed-text-v2-moe",
            dimensions=dimensions,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class FakeLibraryChatAnswerComposer:
    def __init__(self, *, body: str, snippet: str) -> None:
        self._body = body
        self._snippet = snippet
        self.last_question = None
        self.last_context = None

    def compose(self, *, question, context):
        self.last_question = question
        self.last_context = context
        source_unit = context.candidates[0].source_unit
        evidence_ref = EvidenceRef(
            material_id=source_unit.material_id,
            source_unit_id=source_unit.id,
            label=source_unit.file_name,
            locator=source_unit.locator,
            snippet=self._snippet,
        )
        return ChatAnswerResponse(
            summary="자료에서 확인한 답변입니다.",
            items=[
                ChatAnswerItemResponse(
                    id="answer",
                    label="답변",
                    body=self._body,
                    evidence_state=EvidenceState.SUPPORTED,
                    value=None,
                    evidence=[EvidenceRefResponse.from_domain(evidence_ref)],
                )
            ],
        )


class SpyLibraryChatAnswerComposer:
    def __init__(self) -> None:
        self.calls = 0
        self.last_question = None
        self.last_context = None

    def compose(self, *, question, context):
        self.calls += 1
        self.last_question = question
        self.last_context = context
        return ChatAnswerResponse(
            summary="composer contract reached",
            items=[
                ChatAnswerItemResponse(
                    id="answer",
                    label="답변",
                    body="route called LibraryChatAnswerComposer.compose",
                    evidence_state=EvidenceState.MISSING,
                    value=None,
                    evidence=[],
                )
            ],
        )


class FailingRetrievalRepository:
    def upsert_material_records(self, *, material_id: str, records: RetrievalRecords) -> None:
        raise RuntimeError("upsert failed")

    def records_for_materials(self, material_ids):
        return RetrievalRecords(source_units=[], embedding_records=[])

    def match_source_units(self, *, material_ids, query_embedding, limit, similarity_threshold):
        return []

    def clear(self) -> None:
        pass


class FailingObservationSink:
    def record_material_upload(self, record) -> None:
        raise RuntimeError("observation sink failed")
