from __future__ import annotations

from typing import Protocol

from server.answers.candidate import AnswerCandidate
from server.answers.library_chat_payload import caveat_from_payload
from server.core.config import (
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
from server.retrieval.models import AnswerContext


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
    ) -> None:
        self._client = client
        self._prompt = prompt or load_caveat_prompt()

    def extract(
        self, *, question: str, candidate: AnswerCandidate, context: AnswerContext
    ) -> Caveat | None:
        if not context.candidates:
            return None
        try:
            payload = self._client.generate_json(
                system=self._prompt.system_message(),
                user=self._prompt.user_message(
                    question=question,
                    label=candidate.label,
                    value=candidate.value or "(none)",
                    body=candidate.draft_body,
                    source_blocks=_format_source_blocks(context),
                ),
            )
        except OllamaClientError:
            # 조건 추출 호출이 실패하면 조건을 못 본 것으로 둔다(제품을 깨지 않는다).
            # 강등은 일어나지 않지만, 답변 호출이 직접 낸 caveat은 그대로 유효.
            return None
        if not isinstance(payload, dict):
            return None
        return caveat_from_payload(payload)


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
        )
    )


def _format_source_blocks(context: AnswerContext) -> str:
    return "\n\n".join(
        (
            f"source_unit_id: {candidate.source_unit.id}\n"
            f"locator: {candidate.source_unit.locator}\n"
            f"text:\n{candidate.source_unit.text}"
        )
        for candidate in context.candidates
    )
