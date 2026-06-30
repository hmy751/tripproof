from __future__ import annotations

import json
from typing import Protocol

from server.answers.models import ChatAnswerItem
from server.extraction.models import EvidenceState
from server.llm.ollama import (
    OllamaChatJsonClient,
    OllamaChatJsonConfig,
    OllamaClientError,
)
from server.prompts.renderers.answer.answer_body import (
    AnswerBodyPrompt,
    load_answer_body_prompt,
)


class AnswerBodySynthesizer(Protocol):
    def synthesize(
        self, *, question: str, items: list[ChatAnswerItem]
    ) -> dict[str, str] | None:
        """Return synthesized body text by item id, or None to use templates."""


class OllamaAnswerBodySynthesizer:
    """Certified items를 사용자-facing body로만 옮기는 마지막 LLM 호출."""

    def __init__(
        self,
        *,
        client: OllamaChatJsonClient,
        prompt: AnswerBodyPrompt | None = None,
        model: str | None = None,
        seed: int | None = None,
        temperature: float | None = 0.0,
    ) -> None:
        self._client = client
        self._prompt = prompt or load_answer_body_prompt()
        self._model = model
        self._seed = seed
        self._temperature = temperature

    @property
    def prompt(self) -> AnswerBodyPrompt:
        return self._prompt

    def synthesize(
        self, *, question: str, items: list[ChatAnswerItem]
    ) -> dict[str, str] | None:
        if not items:
            return {}
        try:
            payload = self._client.generate_json(
                system=self._prompt.system_message(),
                user=self._prompt.user_message(
                    question=question,
                    certified_items=_format_certified_items(items),
                ),
            )
        except OllamaClientError:
            return None
        return _body_map_from_payload(payload=payload, items=items)

    def runtime_body_model_snapshot(self) -> dict[str, object]:
        return {
            "enabled": True,
            "backend": "ollama",
            "model": self._model,
            "seed": self._seed,
            "temperature": self._temperature,
        }


def create_answer_body_synthesizer_from_config(
    *,
    base_url: str,
    model: str,
    timeout_seconds: float,
    seed: int | None,
) -> AnswerBodySynthesizer:
    return OllamaAnswerBodySynthesizer(
        client=OllamaChatJsonClient(
            OllamaChatJsonConfig(
                base_url=base_url,
                model=model,
                timeout_seconds=timeout_seconds,
                seed=seed,
            )
        ),
        model=model,
        seed=seed,
        temperature=0.0,
    )


def _format_certified_items(items: list[ChatAnswerItem]) -> str:
    payload = []
    for item in items:
        certification = item.certification
        payload.append(
            {
                "id": item.id,
                "label": item.label,
                "state": item.evidence_state.value,
                "value": item.value,
                "certification_reason": (
                    certification.reason if certification is not None else None
                ),
                "evidence_snippets": [evidence.snippet for evidence in item.evidence],
                "caveat_snippet": (
                    certification.caveat.snippet
                    if certification is not None and certification.caveat is not None
                    else None
                ),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _body_map_from_payload(
    *, payload: object, items: list[ChatAnswerItem]
) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return None

    source_by_id = {item.id: item for item in items}
    expected_ids = set(source_by_id)
    bodies: dict[str, str] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            return None
        item_id = _optional_string(raw_item.get("id"))
        body = _optional_string(raw_item.get("body"))
        if item_id is None or body is None:
            return None
        if item_id not in expected_ids or item_id in bodies:
            return None
        if _looks_like_prompt_leak(body):
            return None
        source_item = source_by_id[item_id]
        if (
            source_item.evidence_state == EvidenceState.NEEDS_REVIEW
            and _looks_confirmed(body)
        ):
            return None
        bodies[item_id] = body

    if set(bodies) != expected_ids:
        return None
    return bodies


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = " ".join(value.split())
    return stripped or None


def _looks_like_prompt_leak(body: str) -> bool:
    markers = (
        "{{",
        "}}",
        "short_snake_case_or_null",
        "string or null",
        "source_unit_id",
        "evidence_snippet",
        "certified_items",
    )
    lowered = body.lower()
    return any(marker.lower() in lowered for marker in markers)


def _looks_confirmed(body: str) -> bool:
    confirmed_markers = (
        "확정입니다",
        "확정됩니다",
        "확정된 조건입니다",
        "보장됩니다",
        "보장된 조건입니다",
    )
    return any(marker in body for marker in confirmed_markers)
