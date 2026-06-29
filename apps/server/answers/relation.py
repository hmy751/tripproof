from __future__ import annotations

from typing import Protocol

from server.answers.candidate import AnswerCandidate
from server.answers.library_chat_payload import caveats_from_payload
from server.core.config import (
    CAVEAT_EXTRACTOR_MODE,
    OLLAMA_ANSWER_MODEL,
    OLLAMA_ANSWER_SEED,
    OLLAMA_ANSWER_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
)
from server.extraction.models import Caveat
from server.llm.ollama import (
    OllamaChatJsonClient,
    OllamaChatJsonConfig,
    OllamaClientError,
)
from server.prompts.renderers.answer.caveat import (
    CaveatPrompt,
    load_caveat_prompt,
)
from server.retrieval.models import AnswerContext, RetrievedSource


class CaveatExtractor(Protocol):
    def extract(
        self, *, question: str, candidate: AnswerCandidate, context: AnswerContext
    ) -> Caveat | None:
        """후보 답변을 좌우하는 조건이 source unit에 있으면 역할로 만들어 돌려준다.

        답이나 상태를 만들지 않는다. 조건이 없으면 None.
        """


class OllamaCaveatExtractor:
    """답변 생성과 분리된 호출로 '이 답을 좌우하는 조건'만 추출한다(생성/검증 분리).

    run 17 관찰: "조건 있냐"고 문서째 물으면 gemma3:4b가 무관한 caveat까지 갖다 붙여
    과잉강등이 났다. 그래서 source unit마다 "이 unit이 *이 답을* 제한하나"를 per-unit으로
    판정하게 좁힌다(가). `order_invariant=True`면 후보 순서를 뒤집어 한 번 더 돌려, 두
    순서 모두에서 나온 caveat만 인정한다 — position bias로 한 번만 튄 noise flag를 거른다
    (라-2, `docs/engineering/llm-design.md`의 출력 검증).

    코드는 이 결과(역할)를 읽어 상태를 내릴 뿐 의미를 다시 분류하지 않는다(`06`).
    """

    def __init__(
        self,
        *,
        client: OllamaChatJsonClient,
        prompt: CaveatPrompt | None = None,
        order_invariant: bool = False,
    ) -> None:
        self._client = client
        self._prompt = prompt or load_caveat_prompt()
        self._order_invariant = order_invariant

    def extract(
        self, *, question: str, candidate: AnswerCandidate, context: AnswerContext
    ) -> Caveat | None:
        units = list(context.candidates)
        if not units:
            return None

        forward = self._caveats_for(question=question, candidate=candidate, units=units)
        if not self._order_invariant:
            return forward[0] if forward else None

        # 순서 불변 검증: 후보 순서를 뒤집어 다시 받아, 두 순서 모두에서 나온 것만 인정.
        reverse = self._caveats_for(
            question=question, candidate=candidate, units=list(reversed(units))
        )
        reverse_ids = {
            c.source_unit_id for c in reverse if c.source_unit_id is not None
        }
        stable = [
            c
            for c in forward
            if c.source_unit_id is not None and c.source_unit_id in reverse_ids
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
            # 추출 호출이 실패하면 조건을 못 본 것으로 둔다(제품을 깨지 않는다).
            return []
        if not isinstance(payload, dict):
            return []
        return caveats_from_payload(payload)


def create_caveat_extractor_from_config(
    *, answer_seed: int | None = None
) -> CaveatExtractor:
    seed = OLLAMA_ANSWER_SEED if answer_seed is None else answer_seed
    return OllamaCaveatExtractor(
        client=OllamaChatJsonClient(
            OllamaChatJsonConfig(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_ANSWER_MODEL,
                timeout_seconds=OLLAMA_ANSWER_TIMEOUT_SECONDS,
                seed=seed,
            )
        ),
        order_invariant=CAVEAT_EXTRACTOR_MODE == "order_invariant",
    )


def _format_source_blocks(units: list[RetrievedSource]) -> str:
    return "\n\n".join(
        (
            f"source_unit_id: {unit.source_unit.id}\n"
            f"locator: {unit.source_unit.locator}\n"
            f"text:\n{unit.source_unit.text}"
        )
        for unit in units
    )
