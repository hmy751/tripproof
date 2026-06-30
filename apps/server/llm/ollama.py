from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, request


class OllamaClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class OllamaChatJsonConfig:
    base_url: str
    model: str
    timeout_seconds: float
    seed: int | None = None
    temperature: float = 0.0


class OllamaChatJsonClient:
    def __init__(self, config: OllamaChatJsonConfig) -> None:
        if not config.base_url or not config.model:
            raise OllamaClientError("Ollama base URL and model are required.")
        self._base_url = config.base_url.rstrip("/")
        self._model = config.model
        self._timeout_seconds = config.timeout_seconds
        self._seed = config.seed
        self._temperature = config.temperature

    def generate_json(self, *, system: str, user: str) -> object:
        options: dict[str, object] = {"temperature": self._temperature}
        if self._seed is not None:
            options["seed"] = self._seed
        payload = json.dumps(
            {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "format": "json",
                "options": options,
            }
        ).encode("utf-8")
        http_request = request.Request(
            f"{self._base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(
                http_request, timeout=self._timeout_seconds
            ) as response:
                raw = response.read()
        except (TimeoutError, error.URLError) as exc:
            raise OllamaClientError(f"Ollama chat request failed: {exc}") from exc

        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise OllamaClientError("Ollama chat response was not valid JSON.") from exc

        message = body.get("message") if isinstance(body, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise OllamaClientError(
                "Ollama chat response did not include message content."
            )

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(
                "Ollama message content was not valid JSON."
            ) from exc
