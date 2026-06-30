from __future__ import annotations

from typing import Literal, Protocol

from server.answers.candidate import AnswerCandidate
from server.answers.library_chat_payload import (
    caveat_from_payload,
    caveats_from_payload,
)
from server.core.config import (
    CAVEAT_EXTRACTOR_MODE,
    OLLAMA_CAVEAT_MODEL,
    OLLAMA_CAVEAT_TIMEOUT_SECONDS,
    OLLAMA_ANSWER_SEED,
    OLLAMA_BASE_URL,
)
from server.extraction.models import Caveat
from server.llm.ollama import (
    OllamaChatJsonClient,
    OllamaChatJsonConfig,
    OllamaClientError,
)
from server.prompts.renderers.answer.caveat import (
    CAVEAT_PROMPT_VERSION,
    CaveatPrompt,
    load_caveat_prompt,
)
from server.retrieval.models import AnswerContext, RetrievedSource

CaveatExtractorMode = Literal["document", "pairwise", "order_invariant"]
CAVEAT_PAIRWISE_PROMPT_VERSION = "2026-06-29-pairwise"


class CaveatExtractor(Protocol):
    def extract(
        self, *, question: str, candidate: AnswerCandidate, context: AnswerContext
    ) -> Caveat | None:
        """후보 답변을 좌우하는 조건이 source unit에 있으면 역할로 만들어 돌려준다.

        답이나 상태를 만들지 않는다. 조건이 없으면 None.
        """


class OllamaCaveatExtractor:
    """답변 생성과 분리된 두 번째 호출로 '값을 좌우하는 조건'만 추출한다.

    생성/검증 분리(`docs/engineering/llm-design.md`): 답을 쓴 호출이 자기 답의 조건까지
    겸하면 편향을 상속한다. 여기서는 답·source unit만 받아 조건이 있는지에만 집중한다.
    코드는 이 결과(역할)를 읽어 상태를 내릴 뿐 의미를 다시 분류하지 않는다(`06`).
    """

    def __init__(
        self,
        *,
        client: OllamaChatJsonClient,
        prompt: CaveatPrompt | None = None,
        mode: CaveatExtractorMode = "document",
        model: str | None = None,
        seed: int | None = None,
        temperature: float | None = 0.0,
    ) -> None:
        self._client = client
        self._mode = mode
        self._prompt = prompt or load_caveat_prompt(
            version=(
                CAVEAT_PAIRWISE_PROMPT_VERSION
                if mode in ("pairwise", "order_invariant")
                else CAVEAT_PROMPT_VERSION
            )
        )
        self._model = model
        self._seed = seed
        self._temperature = temperature

    def extract(
        self, *, question: str, candidate: AnswerCandidate, context: AnswerContext
    ) -> Caveat | None:
        units = list(context.candidates)
        if not units:
            return None
        if self._mode in ("pairwise", "order_invariant"):
            return self._extract_pairwise(
                question=question,
                candidate=candidate,
                units=units,
                order_invariant=self._mode == "order_invariant",
            )

        try:
            payload = self._client.generate_json(
                system=self._prompt.system_message(),
                user=self._prompt.user_message(
                    question=question,
                    label=candidate.label,
                    value=candidate.value or "(none)",
                    body=candidate.draft_body,
                    source_blocks=_format_source_blocks(units),
                ),
            )
        except OllamaClientError:
            # 조건 추출 호출이 실패하면 조건을 못 본 것으로 둔다(제품을 깨지 않는다).
            # 강등은 일어나지 않지만, 답변 호출이 직접 낸 caveat은 그대로 유효.
            return None
        if not isinstance(payload, dict):
            return None
        return caveat_from_payload(payload)

    def runtime_relation_model_snapshot(self) -> dict[str, object]:
        return {
            "enabled": True,
            "mode": self._mode,
            "backend": "ollama",
            "model": self._model,
            "seed": self._seed,
            "temperature": self._temperature,
        }

    def _extract_pairwise(
        self,
        *,
        question: str,
        candidate: AnswerCandidate,
        units: list[RetrievedSource],
        order_invariant: bool,
    ) -> Caveat | None:
        forward = self._caveats_for(question=question, candidate=candidate, units=units)
        if not order_invariant:
            return forward[0] if forward else None

        reverse = self._caveats_for(
            question=question, candidate=candidate, units=list(reversed(units))
        )
        reverse_ids = {
            caveat.source_unit_id
            for caveat in reverse
            if caveat.source_unit_id is not None
        }
        stable = [
            caveat
            for caveat in forward
            if caveat.source_unit_id is not None
            and caveat.source_unit_id in reverse_ids
        ]
        return stable[0] if stable else None

    def _caveats_for(
        self,
        *,
        question: str,
        candidate: AnswerCandidate,
        units: list[RetrievedSource],
    ) -> list[Caveat]:
        try:
            payload = self._client.generate_json(
                system=self._prompt.system_message(),
                user=self._prompt.user_message(
                    question=question,
                    label=candidate.label,
                    value=candidate.value or "(none)",
                    body=candidate.draft_body,
                    source_blocks=_format_source_blocks(units),
                ),
            )
        except OllamaClientError:
            return []
        if not isinstance(payload, dict):
            return []
        caveats = caveats_from_payload(payload)
        if caveats:
            return caveats
        caveat = caveat_from_payload(payload)
        return [caveat] if caveat is not None else []


def create_caveat_extractor_from_config(
    *, answer_seed: int | None = None
) -> CaveatExtractor | None:
    mode = _caveat_extractor_mode_from_config(CAVEAT_EXTRACTOR_MODE)
    if mode is None:
        return None
    seed = OLLAMA_ANSWER_SEED if answer_seed is None else answer_seed
    return OllamaCaveatExtractor(
        client=OllamaChatJsonClient(
            OllamaChatJsonConfig(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_CAVEAT_MODEL,
                timeout_seconds=OLLAMA_CAVEAT_TIMEOUT_SECONDS,
                seed=seed,
            )
        ),
        mode=mode,
        model=OLLAMA_CAVEAT_MODEL,
        seed=seed,
        temperature=0.0,
    )


def _caveat_extractor_mode_from_config(value: str) -> CaveatExtractorMode | None:
    normalized = value.strip().lower()
    if normalized in {"", "document"}:
        return "document"
    if normalized == "pairwise":
        return "pairwise"
    if normalized == "order_invariant":
        return "order_invariant"
    if normalized in {"disabled", "off", "none"}:
        return None
    raise ValueError(f"Unsupported caveat extractor mode: {value}")


def _format_source_blocks(units: list[RetrievedSource]) -> str:
    return "\n\n".join(
        (
            f"source_unit_id: {candidate.source_unit.id}\n"
            f"locator: {candidate.source_unit.locator}\n"
            f"text:\n{candidate.source_unit.text}"
        )
        for candidate in units
    )
