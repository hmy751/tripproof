from __future__ import annotations

import json

import pytest

from server.llm.ollama import (
    OllamaChatJsonClient,
    OllamaChatJsonConfig,
    OllamaClientError,
)


def test_ollama_chat_json_client_sends_configured_seed(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"message": {"content": json.dumps({"items": []})}}
            ).encode("utf-8")

    def fake_urlopen(http_request, *, timeout):
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(http_request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr("server.llm.ollama.request.urlopen", fake_urlopen)

    client = OllamaChatJsonClient(
        OllamaChatJsonConfig(
            base_url="http://ollama.local",
            model="gemma3:4b",
            timeout_seconds=12.0,
            seed=1234,
        )
    )

    assert client.generate_json(system="system", user="user") == {"items": []}
    assert captured["url"] == "http://ollama.local/api/chat"
    assert captured["timeout"] == 12.0
    assert captured["payload"]["options"] == {
        "temperature": 0.0,
        "seed": 1234,
    }


def test_ollama_chat_json_client_wraps_timeout(monkeypatch) -> None:
    def fake_urlopen(http_request, *, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr("server.llm.ollama.request.urlopen", fake_urlopen)

    client = OllamaChatJsonClient(
        OllamaChatJsonConfig(
            base_url="http://ollama.local",
            model="qwen3:14b",
            timeout_seconds=1.0,
        )
    )

    with pytest.raises(OllamaClientError, match="timed out"):
        client.generate_json(system="system", user="user")
