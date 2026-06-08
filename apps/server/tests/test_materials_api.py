from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from server.app import create_app
from server.materials.store import MaterialStore
from server.retrieval.embeddings import EmbeddingProfile


def test_upload_text_pdf_returns_ready_material() -> None:
    client = TestClient(create_app())

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


def test_upload_blank_pdf_returns_failed_material() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/materials",
        files={"file": ("blank.pdf", _blank_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    material = response.json()
    assert material["status"] == "failed"
    assert material["pageCount"] is None
    assert material["error"] == "텍스트를 추출할 수 없는 PDF입니다."


def test_question_uses_ready_material_text_context() -> None:
    client = TestClient(create_app())
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
    assert "Check-in starts at 15:00" in body["excerpt"]
    assert body["excerptLocator"] == "booking.pdf p.1 u.1"
    assert body["excerptSourceUnitId"].startswith("su_")


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


def test_question_blocks_when_only_failed_material_exists() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/materials",
        files={"file": ("blank.pdf", _blank_pdf(), "application/pdf")},
    )

    response = client.post("/api/questions", json={"question": "check-in time?"})

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["materialCount"] == 0


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
