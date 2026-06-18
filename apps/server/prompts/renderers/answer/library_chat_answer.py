from __future__ import annotations

from dataclasses import dataclass
import re

from server.prompts.runtime.prompt_document import PromptDocument
from server.prompts.runtime.prompt_store import load_prompt_document

LIBRARY_CHAT_PROMPT_DOMAIN = "answer"
LIBRARY_CHAT_PROMPT_NAME = "library_chat_answer"
LIBRARY_CHAT_PROMPT_VERSION = "2026-06-10"
REQUIRED_TEMPLATE_VARIABLES = frozenset({"question", "source_blocks"})


@dataclass(frozen=True)
class LibraryChatAnswerPrompt:
    document: PromptDocument

    def system_message(self) -> str:
        return ""

    def user_message(self, *, question: str, source_blocks: str) -> str:
        return _render_template(
            self.document.body_markdown,
            question=question,
            source_blocks=source_blocks,
        )

    def snapshot(self) -> dict[str, str]:
        return self.document.snapshot()


def load_library_chat_answer_prompt(
    version: str = LIBRARY_CHAT_PROMPT_VERSION,
) -> LibraryChatAnswerPrompt:
    return LibraryChatAnswerPrompt(
        document=load_prompt_document(
            domain=LIBRARY_CHAT_PROMPT_DOMAIN,
            name=LIBRARY_CHAT_PROMPT_NAME,
            version=version,
        )
    )


def _render_template(template: str, **values: str) -> str:
    required_missing = sorted(
        REQUIRED_TEMPLATE_VARIABLES - _template_variables(template)
    )
    if required_missing:
        raise ValueError(
            "Library Chat answer prompt에 필요한 placeholder가 없습니다: "
            f"{', '.join(required_missing)}"
        )

    rendered = template
    for key, value in values.items():
        rendered = re.sub(
            r"{{\s*" + re.escape(key) + r"\s*}}", lambda _: value, rendered
        )
    missing = sorted(_template_variables(rendered))
    if missing:
        raise ValueError(
            f"Library Chat answer prompt 렌더링 값이 없습니다: {', '.join(missing)}"
        )
    return rendered


def _template_variables(template: str) -> set[str]:
    return set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", template))
