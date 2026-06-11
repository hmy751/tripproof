from __future__ import annotations

from io import BytesIO
import json

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
from server.observations.export import LocalArtifactObservationExporter, NoopObservationExporter
from server.observations.langsmith import LangSmithObservationExporter
from server.prompts.renderers.answer.library_chat_answer import load_library_chat_answer_prompt
from server.questions.observation import InMemoryQuestionObservationSink
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
    assert "runtimeConfig" not in material

    records = observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.operation == "material_upload"
    assert record.material_id == material["id"]
    assert _step_names(record) == [
        "material_intake",
        "content_extraction",
        "retrieval_preparation",
        "finalization",
    ]
    assert _child_step_names(record.step("material_intake")) == ["upload_snapshot"]
    assert record.step("material_intake").status == "succeeded"
    assert record.step("upload_snapshot").status == "succeeded"
    assert record.step("upload_snapshot").facts["file_name"] == "booking.pdf"
    assert record.step("upload_snapshot").facts["content_type"] == "application/pdf"
    assert record.step("upload_snapshot").facts["size_bytes"] > 0
    assert _child_step_names(record.step("content_extraction")) == ["pdf_parse"]
    assert record.step("content_extraction").status == "succeeded"
    assert record.step("pdf_parse").status == "succeeded"
    assert record.step("pdf_parse").facts == {"page_count": 1}
    assert _child_step_names(record.step("retrieval_preparation")) == [
        "source_unit_build",
        "embedding_record_build",
        "retrieval_repository_upsert",
    ]
    assert record.step("retrieval_preparation").status == "succeeded"
    assert record.step("source_unit_build").status == "succeeded"
    assert record.step("source_unit_build").facts == {"count": 1}
    assert record.step("embedding_record_build").status == "succeeded"
    assert record.step("embedding_record_build").facts == {
        "count": 1,
        "status_counts": {"pending": 1},
    }
    assert record.step("retrieval_repository_upsert").status == "succeeded"
    assert record.step("retrieval_repository_upsert").facts == {
        "executed": True,
        "source_unit_count": 1,
        "embedding_record_count": 1,
    }
    assert _child_step_names(record.step("finalization")) == ["material_status"]
    assert record.step("finalization").status == "succeeded"
    assert record.step("material_status").status == "succeeded"
    assert record.step("material_status").facts == {"status": "ready"}
    assert record.final_material_status == "ready"
    assert record.failure_kind is None
    assert record.runtime_config_snapshot is not None
    assert record.runtime_config_snapshot.retrieval.backend == "memory"
    assert record.runtime_config_snapshot.retrieval.top_k == 3
    assert record.runtime_config_snapshot.retrieval.similarity_threshold == 0.0
    assert record.runtime_config_snapshot.embedding.auto_generate is False
    assert record.runtime_config_snapshot.embedding.provider == "ollama"
    assert record.runtime_config_snapshot.embedding.model == "nomic-embed-text-v2-moe"
    assert record.runtime_config_snapshot.embedding.dimensions == 768
    assert record.runtime_config_snapshot.prompt is None
    assert record.runtime_config_snapshot.answer_model is None


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
    assert record.step("material_intake").status == "succeeded"
    assert record.step("upload_snapshot").status == "succeeded"
    assert record.step("content_extraction").status == "failed"
    assert record.step("pdf_parse").status == "failed"
    assert record.step("pdf_parse").failure_kind == "parse_failed"
    assert record.step("retrieval_preparation").status == "not_started"
    assert record.step("source_unit_build").status == "not_started"
    assert record.step("embedding_record_build").status == "not_started"
    assert record.step("retrieval_repository_upsert").status == "not_started"
    assert record.step("finalization").status == "succeeded"
    assert record.step("material_status").facts == {"status": "failed"}
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
    assert record.step("material_intake").status == "failed"
    assert record.step("upload_snapshot").facts["file_name"] == "notes.txt"
    assert record.step("upload_snapshot").facts["content_type"] == "text/plain"
    assert record.step("upload_snapshot").status == "failed"
    assert record.step("upload_snapshot").failure_kind == "unsupported_file"
    assert record.step("content_extraction").status == "not_started"
    assert record.step("pdf_parse").status == "not_started"
    assert record.step("finalization").status == "succeeded"
    assert record.step("material_status").facts == {"status": "failed"}
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
    assert record.step("material_intake").status == "failed"
    assert record.step("upload_snapshot").facts["file_name"] == "booking.pdf"
    assert record.step("upload_snapshot").facts["size_bytes"] == len(b"%PDF-too-large")
    assert record.step("upload_snapshot").facts["size_limit_bytes"] == 5
    assert record.step("upload_snapshot").status == "failed"
    assert record.step("upload_snapshot").failure_kind == "size_limit_exceeded"
    assert record.step("content_extraction").status == "not_started"
    assert record.step("pdf_parse").status == "not_started"
    assert record.step("finalization").status == "succeeded"
    assert record.step("material_status").facts == {"status": "failed"}
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


def test_local_artifact_observation_exporter_records_material_and_question_payloads(tmp_path) -> None:
    exporter = LocalArtifactObservationExporter(tmp_path)
    composer = FakeLibraryChatAnswerComposer(
        body="체크인 시작 시각은 15:00입니다.",
        snippet="Check-in starts at 15:00.",
    )
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=composer,
            observation_exporter=exporter,
        )
    )
    upload = client.post(
        "/api/materials",
        files={
            "file": (
                "booking-secret-name.pdf",
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
    assert "observation" not in body
    assert "runtimeConfig" not in body

    rows = [json.loads(line) for line in exporter.path.read_text(encoding="utf-8").splitlines()]
    assert [row["schema_version"] for row in rows] == [
        "tripproof.observation_export.v1",
        "tripproof.observation_export.v1",
    ]
    assert [row["operation"] for row in rows] == ["material_upload", "question_answer"]

    material_export = rows[0]
    assert material_export["payload"]["final_status"] == "ready"
    assert material_export["payload"]["failure_kind"] is None
    assert material_export["payload"]["subject"] == {"material_id": material_id}
    assert material_export["payload"]["runtime_config_snapshot"]["retrieval"] == {
        "backend": "memory",
        "top_k": 3,
        "similarity_threshold": 0.0,
    }
    upload_facts = _export_step(material_export, "upload_snapshot")["facts"]
    assert upload_facts["file_name_present"] is True
    assert upload_facts["file_extension"] == "pdf"
    assert "file_name" not in upload_facts
    assert upload_facts["content_type"] == "application/pdf"

    question_export = rows[1]
    assert question_export["payload"]["final_status"] == "accepted"
    assert question_export["payload"]["failure_kind"] is None
    assert _export_step(question_export, "ready_material_selection")["facts"] == {
        "ready_material_count": 1,
        "ready_material_ids": [material_id],
    }
    assert _export_step(question_export, "question_status")["facts"] == {"status": "accepted"}

    exported_json = json.dumps(rows, ensure_ascii=False)
    assert "booking-secret-name.pdf" not in exported_json
    assert "check-in time?" not in exported_json
    assert "Hotel address is Hakata" not in exported_json
    assert "체크인 시작 시각은 15:00입니다." not in exported_json


def test_langsmith_observation_exporter_records_safe_material_and_question_runs() -> None:
    writer = SpyLangSmithRunWriter()
    exporter = LangSmithObservationExporter(writer)
    composer = FakeLibraryChatAnswerComposer(
        body="체크인 시작 시각은 15:00입니다.",
        snippet="Check-in starts at 15:00.",
    )
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=composer,
            observation_exporter=exporter,
        )
    )
    upload = client.post(
        "/api/materials",
        files={
            "file": (
                "booking-secret-name.pdf",
                _pdf_with_text("Hotel address is Hakata. Check-in starts at 15:00."),
                "application/pdf",
            )
        },
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert upload.status_code == 200
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert [run["name"] for run in writer.runs] == [
        "tripproof.material_upload",
        "tripproof.question_answer",
    ]

    material_run = writer.runs[0]
    assert material_run["run_type"] == "chain"
    assert material_run["inputs"] == {
        "operation": "material_upload",
        "subject": {"material_id": material_id},
    }
    assert material_run["outputs"] == {"final_status": "ready", "failure_kind": None}
    assert material_run["metadata"]["tripproof.schema_version"] == "tripproof.observation_export.v1"
    assert material_run["metadata"]["tripproof.retrieval_backend"] == "memory"
    assert material_run["metadata"]["tripproof.embedding_provider"] == "ollama"
    assert [child["name"] for child in material_run["child_runs"]] == [
        "material_intake",
        "content_extraction",
        "retrieval_preparation",
        "finalization",
    ]
    material_intake = _langsmith_child_run(material_run, "material_intake")
    assert material_intake["metadata"]["tripproof.synthetic_observation_step"] is True
    assert material_intake["metadata"]["tripproof.step.kind"] == "parent_step"
    assert [child["name"] for child in material_intake["children"]] == ["upload_snapshot"]
    upload_child = _langsmith_child_run(material_intake, "upload_snapshot")
    assert upload_child["outputs"]["status"] == "succeeded"
    assert upload_child["outputs"]["failure_kind"] is None
    assert upload_child["outputs"]["facts"]["file_name_present"] is True
    assert upload_child["outputs"]["facts"]["file_extension"] == "pdf"
    assert upload_child["metadata"]["tripproof.step.kind"] == "leaf_step"
    assert upload_child["metadata"]["tripproof.step.facts"]["file_name_present"] is True
    assert upload_child["metadata"]["tripproof.step.facts"]["file_extension"] == "pdf"
    assert "file_name" not in upload_child["metadata"]["tripproof.step.facts"]
    retrieval_preparation = _langsmith_child_run(material_run, "retrieval_preparation")
    assert retrieval_preparation["metadata"]["tripproof.runtime_hint.retrieval_backend"] == "memory"
    embedding_record_build = _langsmith_child_run(material_run, "embedding_record_build")
    assert embedding_record_build["metadata"]["tripproof.runtime_hint.embedding_provider"] == "ollama"
    assert (
        embedding_record_build["metadata"]["tripproof.runtime_hint.embedding_model"]
        == "nomic-embed-text-v2-moe"
    )
    upload_event = _langsmith_event(material_run, "upload_snapshot")
    assert upload_event["kwargs"]["kind"] == "leaf_step"
    assert upload_event["kwargs"]["facts"]["file_name_present"] is True
    assert upload_event["kwargs"]["facts"]["file_extension"] == "pdf"
    assert "file_name" not in upload_event["kwargs"]["facts"]

    question_run = writer.runs[1]
    assert question_run["inputs"] == {"operation": "question_answer", "subject": {}}
    assert question_run["outputs"] == {"final_status": "accepted", "failure_kind": None}
    assert [child["name"] for child in question_run["child_runs"]] == [
        "question_preparation",
        "material_scope",
        "retrieval_pipeline",
        "answer_pipeline",
        "finalization",
    ]
    answer_pipeline = _langsmith_child_run(question_run, "answer_pipeline")
    assert [child["name"] for child in answer_pipeline["children"]] == [
        "prompt_snapshot",
        "composer_call",
        "answer_projection",
    ]
    answer_projection = _langsmith_child_run(answer_pipeline, "answer_projection")
    assert answer_projection["outputs"]["facts"] == {
        "item_count": 1,
        "evidence_state_counts": {"supported": 1},
    }
    assert answer_projection["metadata"]["tripproof.step.facts"] == {
        "item_count": 1,
        "evidence_state_counts": {"supported": 1},
    }
    retrieval_pipeline = _langsmith_child_run(question_run, "retrieval_pipeline")
    assert retrieval_pipeline["metadata"]["tripproof.runtime_hint.retrieval_backend"] == "memory"
    source_retrieval = _langsmith_child_run(question_run, "source_retrieval")
    assert source_retrieval["metadata"]["tripproof.runtime_hint.embedding_provider"] == "ollama"
    assert _langsmith_event(question_run, "query_snapshot")["kwargs"]["facts"] == {
        "question_length": len("check-in time?"),
    }
    assert _langsmith_event(question_run, "ready_material_selection")["kwargs"]["facts"] == {
        "ready_material_count": 1,
        "ready_material_ids": [material_id],
    }
    assert _langsmith_event(question_run, "answer_projection")["kwargs"]["facts"] == {
        "item_count": 1,
        "evidence_state_counts": {"supported": 1},
    }

    exported_json = json.dumps(writer.runs, ensure_ascii=False)
    assert "booking-secret-name.pdf" not in exported_json
    assert "check-in time?" not in exported_json
    assert "Hotel address is Hakata" not in exported_json
    assert "Check-in starts at 15:00." not in exported_json
    assert "체크인 시작 시각은 15:00입니다." not in exported_json


def test_langsmith_observation_exporter_failure_does_not_change_product_responses() -> None:
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=SpyLibraryChatAnswerComposer(),
            observation_exporter=LangSmithObservationExporter(FailingLangSmithRunWriter()),
        )
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material = upload.json()

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material["id"]]})

    assert upload.status_code == 200
    assert material["status"] == "ready"
    assert "observation" not in material
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert "observation" not in body
    assert "debug" not in body
    assert "raw" not in body


def test_default_observation_exporter_uses_noop_when_langsmith_enabled_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(server_app, "LANGSMITH_OBSERVATION_ENABLED", True)
    monkeypatch.setattr(server_app, "LANGSMITH_API_KEY", "")
    monkeypatch.setattr(server_app, "OBSERVATION_EXPORT_DIR", "")

    exporter = server_app._create_default_observation_exporter()

    assert isinstance(exporter, NoopObservationExporter)


def test_observation_exporter_failure_does_not_change_product_responses() -> None:
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=SpyLibraryChatAnswerComposer(),
            observation_exporter=FailingObservationExporter(),
        )
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material = upload.json()

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material["id"]]})

    assert upload.status_code == 200
    assert material["status"] == "ready"
    assert "observation" not in material
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert "observation" not in body
    assert "debug" not in body
    assert "raw" not in body


def test_question_returns_chat_answer_for_ready_materials() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    composer = FakeLibraryChatAnswerComposer(
        body="체크인 시작 시각은 15:00입니다.",
        snippet="Check-in starts at 15:00.",
    )
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=composer,
            question_observation_sink=question_observation_sink,
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
    assert "observation" not in body
    assert "debug" not in body
    assert "raw" not in body
    assert "runtimeConfig" not in body
    assert "excerpt" not in body
    assert "facts" not in body

    records = question_observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.operation == "question_answer"
    assert _step_names(record) == [
        "question_preparation",
        "material_scope",
        "retrieval_pipeline",
        "answer_pipeline",
        "finalization",
    ]
    assert _child_step_names(record.step("question_preparation")) == ["query_snapshot"]
    assert record.step("query_snapshot").status == "succeeded"
    assert record.step("query_snapshot").facts == {"question_length": len("check-in time?")}
    assert _child_step_names(record.step("material_scope")) == [
        "ready_material_selection",
        "retrieval_record_load",
    ]
    assert record.step("ready_material_selection").status == "succeeded"
    assert record.step("ready_material_selection").facts == {
        "ready_material_count": 1,
        "ready_material_ids": [material_id],
    }
    assert record.step("material_scope").status == "succeeded"
    assert _child_step_names(record.step("retrieval_pipeline")) == [
        "source_retrieval",
        "context_assembly",
        "candidate_summary",
    ]
    assert record.step("retrieval_pipeline").status == "succeeded"
    assert record.step("retrieval_record_load").status == "succeeded"
    assert record.step("retrieval_record_load").facts == {
        "executed": True,
        "source_unit_count": 1,
        "embedding_record_count": 1,
    }
    assert record.step("source_retrieval").status == "succeeded"
    assert record.step("source_retrieval").facts == {
        "executed": True,
        "strategy": "lexical",
        "query_embedding_attempted": False,
        "query_embedding_available": False,
        "vector_attempted": False,
        "vector_candidate_count": 0,
        "fallback_used": False,
    }
    assert record.step("context_assembly").status == "succeeded"
    assert record.step("context_assembly").facts == {
        "executed": True,
        "target_id": "library_chat_answer",
    }
    assert record.step("candidate_summary").status == "succeeded"
    assert record.step("candidate_summary").facts == {
        "candidate_count": 1,
        "candidates_with_vector_score": 0,
        "candidates_with_lexical_score": 1,
    }
    assert _child_step_names(record.step("answer_pipeline")) == [
        "prompt_snapshot",
        "composer_call",
        "answer_projection",
    ]
    assert record.step("answer_pipeline").status == "succeeded"
    assert record.step("prompt_snapshot").status == "succeeded"
    assert record.step("prompt_snapshot").facts == {"available": False}
    assert record.step("composer_call").status == "succeeded"
    assert record.step("composer_call").facts == {"result": "succeeded"}
    assert record.step("answer_projection").status == "succeeded"
    assert record.step("answer_projection").facts == {
        "item_count": 1,
        "evidence_state_counts": {"supported": 1},
    }
    assert _child_step_names(record.step("finalization")) == ["question_status"]
    assert record.step("finalization").status == "succeeded"
    assert record.step("question_status").status == "succeeded"
    assert record.step("question_status").facts == {"status": "accepted"}
    assert record.final_question_status == "accepted"
    assert record.failure_kind is None
    assert record.runtime_config_snapshot is not None
    assert record.runtime_config_snapshot.retrieval.backend == "memory"
    assert record.runtime_config_snapshot.retrieval.top_k == 3
    assert record.runtime_config_snapshot.retrieval.similarity_threshold == 0.0
    assert record.runtime_config_snapshot.embedding.auto_generate is False
    assert record.runtime_config_snapshot.embedding.provider == "ollama"
    assert record.runtime_config_snapshot.embedding.model == "nomic-embed-text-v2-moe"
    assert record.runtime_config_snapshot.embedding.dimensions == 768
    assert record.runtime_config_snapshot.prompt is None
    assert record.runtime_config_snapshot.answer_model is None


def test_question_observation_records_repository_vector_source_retrieval() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    composer = FakeLibraryChatAnswerComposer(
        body="체크인 시작 시각은 15:00입니다.",
        snippet="Check-in starts at 15:00.",
    )
    repository = TrackingRetrievalRepository()
    store = MaterialStore(
        embedding_provider=FakeEmbeddingProvider(dimensions=3),
        embedding_auto_generate=True,
        retrieval_repository=repository,
    )
    client = TestClient(
        create_app(
            store=store,
            retrieval_top_k=1,
            retrieval_similarity_threshold=0.25,
            library_chat_answer_composer=composer,
            question_observation_sink=question_observation_sink,
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
    record = question_observation_sink.records[0]
    assert repository.seen_limit == 1
    assert repository.seen_similarity_threshold == 0.25
    assert record.step("source_retrieval").facts == {
        "executed": True,
        "strategy": "repository_vector",
        "query_embedding_attempted": True,
        "query_embedding_available": True,
        "vector_attempted": True,
        "vector_candidate_count": 1,
        "fallback_used": False,
    }
    assert record.step("candidate_summary").facts["candidate_count"] == 1
    assert record.step("candidate_summary").facts["candidates_with_vector_score"] == 1
    assert record.runtime_config_snapshot is not None
    assert record.runtime_config_snapshot.retrieval.backend == "memory"
    assert record.runtime_config_snapshot.retrieval.top_k == 1
    assert record.runtime_config_snapshot.retrieval.similarity_threshold == 0.25
    assert record.runtime_config_snapshot.embedding.auto_generate is True
    assert record.runtime_config_snapshot.embedding.provider == "ollama"
    assert record.runtime_config_snapshot.embedding.model == "nomic-embed-text-v2-moe"
    assert record.runtime_config_snapshot.embedding.dimensions == 3
    assert composer.last_context is not None
    assert composer.last_context.candidates[0].vector_score is not None


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


def test_question_observation_records_prompt_snapshot_when_composer_exposes_prompt() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=PromptAwareSpyLibraryChatAnswerComposer(),
            question_observation_sink=question_observation_sink,
        )
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 200
    prompt_snapshot = load_library_chat_answer_prompt().snapshot()
    record = question_observation_sink.records[0]
    assert record.runtime_config_snapshot is not None
    assert record.runtime_config_snapshot.prompt is not None
    assert record.runtime_config_snapshot.prompt.domain == "answer"
    assert record.runtime_config_snapshot.prompt.name == "library_chat_answer"
    assert record.runtime_config_snapshot.prompt.version == "2026-06-10"
    assert record.runtime_config_snapshot.prompt.body_hash == prompt_snapshot["bodyHash"]
    assert record.runtime_config_snapshot.prompt.file_hash == prompt_snapshot["fileHash"]
    assert (
        record.runtime_config_snapshot.prompt.asset_path
        == "apps/server/prompts/assets/answer/library_chat_answer/2026-06-10.md"
    )
    assert record.step("prompt_snapshot").facts == {
        "available": True,
        "prompt_domain": "answer",
        "prompt_name": "library_chat_answer",
        "prompt_version": "2026-06-10",
        "prompt_body_hash": prompt_snapshot["bodyHash"],
        "prompt_file_hash": prompt_snapshot["fileHash"],
        "prompt_asset_path": "apps/server/prompts/assets/answer/library_chat_answer/2026-06-10.md",
    }
    body = response.json()
    assert "observation" not in body
    assert "debug" not in body
    assert "raw" not in body
    assert "runtimeConfig" not in body


def test_question_runtime_config_snapshot_records_configured_answer_model() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            fact_proposer_backend="disabled",
            question_observation_sink=question_observation_sink,
        )
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 200
    body = response.json()
    assert "runtimeConfig" not in body
    record = question_observation_sink.records[0]
    assert record.runtime_config_snapshot is not None
    assert record.runtime_config_snapshot.answer_model is not None
    assert record.runtime_config_snapshot.answer_model.backend == "disabled"
    assert record.runtime_config_snapshot.answer_model.model is None


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
    assert record.step("material_intake").status == "succeeded"
    assert record.step("upload_snapshot").status == "succeeded"
    assert record.step("pdf_parse").status == "succeeded"
    assert record.step("retrieval_preparation").status == "failed"
    assert record.step("retrieval_preparation").failure_kind == "repository_upsert_failed"
    assert record.step("source_unit_build").status == "succeeded"
    assert record.step("source_unit_build").facts == {"count": 1}
    assert record.step("embedding_record_build").status == "succeeded"
    assert record.step("embedding_record_build").facts == {
        "count": 1,
        "status_counts": {"pending": 1},
    }
    assert record.step("retrieval_repository_upsert").status == "failed"
    assert record.step("retrieval_repository_upsert").facts == {
        "executed": True,
        "source_unit_count": 1,
        "embedding_record_count": 1,
    }
    assert record.step("retrieval_repository_upsert").failure_kind == "repository_upsert_failed"
    assert record.step("finalization").status == "succeeded"
    assert record.step("material_status").facts == {"status": "failed"}
    assert record.final_material_status == "failed"
    assert record.failure_kind == "repository_upsert_failed"


def test_question_blocks_when_only_failed_material_exists() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            question_observation_sink=question_observation_sink,
        )
    )
    client.post(
        "/api/materials",
        files={"file": ("blank.pdf", _blank_pdf(), "application/pdf")},
    )

    response = client.post("/api/questions", json={"question": "check-in time?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["materialCount"] == 0
    assert "observation" not in body
    assert "debug" not in body
    assert "raw" not in body

    records = question_observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.step("query_snapshot").status == "succeeded"
    assert record.step("query_snapshot").facts == {"question_length": len("check-in time?")}
    assert record.step("ready_material_selection").status == "failed"
    assert record.step("ready_material_selection").failure_kind == "no_ready_materials"
    assert record.step("ready_material_selection").facts == {
        "ready_material_count": 0,
        "ready_material_ids": [],
    }
    assert record.step("material_scope").status == "failed"
    assert record.step("retrieval_record_load").status == "not_started"
    assert record.step("retrieval_pipeline").status == "not_started"
    assert record.step("answer_pipeline").status == "not_started"
    assert record.step("finalization").status == "succeeded"
    assert record.step("question_status").status == "succeeded"
    assert record.step("question_status").facts == {"status": "blocked"}
    assert record.final_question_status == "blocked"
    assert record.failure_kind == "no_ready_materials"


def test_question_records_empty_question_validation_failure() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            question_observation_sink=question_observation_sink,
        )
    )

    response = client.post("/api/questions", json={"question": "   "})

    assert response.status_code == 400
    records = question_observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.step("question_preparation").status == "failed"
    assert record.step("query_snapshot").status == "failed"
    assert record.step("query_snapshot").failure_kind == "empty_question"
    assert record.step("query_snapshot").facts == {"question_length": 0}
    assert record.step("material_scope").status == "not_started"
    assert record.step("retrieval_pipeline").status == "not_started"
    assert record.step("answer_pipeline").status == "not_started"
    assert record.step("finalization").status == "not_started"
    assert record.final_question_status is None
    assert record.failure_kind == "empty_question"


def test_question_observation_sink_failure_does_not_change_accepted_response() -> None:
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=SpyLibraryChatAnswerComposer(),
            question_observation_sink=FailingQuestionObservationSink(),
        )
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert "observation" not in body
    assert "debug" not in body
    assert "raw" not in body


def test_question_records_retrieval_failure_without_changing_exception_behavior() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    store = MaterialStore(retrieval_repository=FailingReadRetrievalRepository())
    client = TestClient(
        create_app(
            store=store,
            library_chat_answer_composer=SpyLibraryChatAnswerComposer(),
            question_observation_sink=question_observation_sink,
        ),
        raise_server_exceptions=False,
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 500
    records = question_observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.step("query_snapshot").status == "succeeded"
    assert record.step("ready_material_selection").status == "succeeded"
    assert record.step("ready_material_selection").facts == {
        "ready_material_count": 1,
        "ready_material_ids": [material_id],
    }
    assert record.step("material_scope").status == "failed"
    assert record.step("material_scope").failure_kind == "retrieval_failed"
    assert record.step("retrieval_record_load").status == "failed"
    assert record.step("retrieval_record_load").failure_kind == "retrieval_failed"
    assert record.step("retrieval_record_load").facts == {"executed": True}
    assert record.step("retrieval_pipeline").status == "not_started"
    assert record.step("source_retrieval").status == "not_started"
    assert record.step("context_assembly").status == "not_started"
    assert record.step("candidate_summary").status == "not_started"
    assert record.step("answer_pipeline").status == "not_started"
    assert record.step("finalization").status == "not_started"
    assert record.final_question_status is None
    assert record.failure_kind == "retrieval_failed"


def test_question_records_answer_composer_failure_without_changing_exception_behavior() -> None:
    question_observation_sink = InMemoryQuestionObservationSink()
    client = TestClient(
        create_app(
            embedding_auto_generate=False,
            retrieval_backend="memory",
            library_chat_answer_composer=FailingLibraryChatAnswerComposer(),
            question_observation_sink=question_observation_sink,
        ),
        raise_server_exceptions=False,
    )
    upload = client.post(
        "/api/materials",
        files={"file": ("booking.pdf", _pdf_with_text("Check-in starts at 15:00."), "application/pdf")},
    )
    material_id = upload.json()["id"]

    response = client.post("/api/questions", json={"question": "check-in time?", "materialIds": [material_id]})

    assert response.status_code == 500
    records = question_observation_sink.records
    assert len(records) == 1
    record = records[0]
    assert record.step("query_snapshot").status == "succeeded"
    assert record.step("ready_material_selection").status == "succeeded"
    assert record.step("retrieval_pipeline").status == "succeeded"
    assert record.step("candidate_summary").facts == {
        "candidate_count": 1,
        "candidates_with_vector_score": 0,
        "candidates_with_lexical_score": 1,
    }
    assert record.step("answer_pipeline").status == "failed"
    assert record.step("prompt_snapshot").status == "succeeded"
    assert record.step("prompt_snapshot").facts == {"available": False}
    assert record.step("composer_call").status == "failed"
    assert record.step("composer_call").failure_kind == "answer_composer_failed"
    assert record.step("answer_projection").status == "not_started"
    assert record.step("finalization").status == "not_started"
    assert record.final_question_status is None
    assert record.failure_kind == "answer_composer_failed"


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


def _child_step_names(step) -> list[str]:
    return [child.name for child in step.children]


def _export_step(export, name: str):
    for step in export["payload"]["steps"]:
        match = _find_export_step(step, name)
        if match is not None:
            return match
    raise KeyError(name)


def _find_export_step(step, name: str):
    if step["name"] == name:
        return step
    for child in step["children"]:
        match = _find_export_step(child, name)
        if match is not None:
            return match
    return None


def _langsmith_event(run, step_name: str):
    for event in run["events"]:
        if event["kwargs"]["name"] == step_name:
            return event
    raise KeyError(step_name)


def _langsmith_child_run(run, step_name: str):
    children = run.get("child_runs", run.get("children", []))
    for child in children:
        if child["name"] == step_name:
            return child
    for child in children:
        try:
            return _langsmith_child_run(child, step_name)
        except KeyError:
            continue
    raise KeyError(step_name)


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


class PromptAwareSpyLibraryChatAnswerComposer(SpyLibraryChatAnswerComposer):
    def __init__(self) -> None:
        super().__init__()
        self.prompt = load_library_chat_answer_prompt()


class FailingLibraryChatAnswerComposer:
    def compose(self, *, question, context):
        raise RuntimeError("answer composer failed")


class FailingRetrievalRepository:
    def upsert_material_records(self, *, material_id: str, records: RetrievalRecords) -> None:
        raise RuntimeError("upsert failed")

    def records_for_materials(self, material_ids):
        return RetrievalRecords(source_units=[], embedding_records=[])

    def match_source_units(self, *, material_ids, query_embedding, limit, similarity_threshold):
        return []

    def clear(self) -> None:
        pass


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


class TrackingRetrievalRepository(InMemoryRetrievalRepository):
    def __init__(self) -> None:
        super().__init__()
        self.seen_limit = None
        self.seen_similarity_threshold = None

    def match_source_units(self, *, material_ids, query_embedding, limit, similarity_threshold):
        self.seen_limit = limit
        self.seen_similarity_threshold = similarity_threshold
        return super().match_source_units(
            material_ids=material_ids,
            query_embedding=query_embedding,
            limit=limit,
            similarity_threshold=similarity_threshold,
        )


class FailingObservationSink:
    def record_material_upload(self, record) -> None:
        raise RuntimeError("observation sink failed")


class FailingQuestionObservationSink:
    def record_question_answer(self, record) -> None:
        raise RuntimeError("question observation sink failed")


class FailingObservationExporter:
    def export_observation(self, envelope) -> None:
        raise RuntimeError("observation export failed")


class SpyLangSmithRunWriter:
    def __init__(self) -> None:
        self.runs = []

    def write_run(self, **kwargs) -> None:
        self.runs.append(kwargs)


class FailingLangSmithRunWriter:
    def write_run(self, **kwargs) -> None:
        raise RuntimeError("langsmith write failed")
