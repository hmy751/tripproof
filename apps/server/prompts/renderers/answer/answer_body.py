from __future__ import annotations

from dataclasses import dataclass
import re

from server.prompts.runtime.prompt_document import PromptDocument
from server.prompts.runtime.prompt_store import load_prompt_document

ANSWER_BODY_PROMPT_DOMAIN = "answer"
ANSWER_BODY_PROMPT_NAME = "answer_body"
ANSWER_BODY_PROMPT_VERSION = "2026-06-30"


@dataclass(frozen=True)
class AnswerBodyPrompt:
    document: PromptDocument

    def system_message(self) -> str:
        return _required_section(markdown=self.document.body_markdown, heading="System")

    def user_message(self, *, question: str, certified_items: str) -> str:
        template = _required_section(
            markdown=self.document.body_markdown, heading="User"
        )
        return _render_template(
            template, question=question, certified_items=certified_items
        )

    def snapshot(self) -> dict[str, str]:
        return self.document.snapshot()


def load_answer_body_prompt(
    version: str = ANSWER_BODY_PROMPT_VERSION,
) -> AnswerBodyPrompt:
    return AnswerBodyPrompt(
        document=load_prompt_document(
            domain=ANSWER_BODY_PROMPT_DOMAIN,
            name=ANSWER_BODY_PROMPT_NAME,
            version=version,
        )
    )


def _required_section(*, markdown: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(f"Answer body prompt에 필요한 section이 없습니다: {heading}")
    body = match.group("body").strip()
    if not body:
        raise ValueError(
            f"Answer body prompt section 본문은 비어 있을 수 없습니다: {heading}"
        )
    return body


def _render_template(template: str, **values: str) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    missing = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", rendered)))
    if missing:
        raise ValueError(
            f"Answer body prompt 렌더링 값이 없습니다: {', '.join(missing)}"
        )
    return rendered
