from __future__ import annotations

from dataclasses import dataclass
import re

from server.prompts.runtime.prompt_document import PromptDocument
from server.prompts.runtime.prompt_store import load_prompt_document

GOVERNING_CONDITION_PROMPT_DOMAIN = "answer"
GOVERNING_CONDITION_PROMPT_NAME = "governing_condition"
GOVERNING_CONDITION_PROMPT_VERSION = "2026-06-29"


@dataclass(frozen=True)
class GoverningConditionPrompt:
    document: PromptDocument

    def system_message(self) -> str:
        return _required_section(markdown=self.document.body_markdown, heading="System")

    def user_message(
        self,
        *,
        question: str,
        label: str,
        value: str,
        body: str,
        source_blocks: str,
    ) -> str:
        template = _required_section(
            markdown=self.document.body_markdown, heading="User"
        )
        return _render_template(
            template,
            question=question,
            label=label,
            value=value,
            body=body,
            source_blocks=source_blocks,
        )

    def snapshot(self) -> dict[str, str]:
        return self.document.snapshot()


def load_governing_condition_prompt(
    version: str = GOVERNING_CONDITION_PROMPT_VERSION,
) -> GoverningConditionPrompt:
    return GoverningConditionPrompt(
        document=load_prompt_document(
            domain=GOVERNING_CONDITION_PROMPT_DOMAIN,
            name=GOVERNING_CONDITION_PROMPT_NAME,
            version=version,
        )
    )


def _required_section(*, markdown: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    if match is None:
        raise ValueError(
            f"Governing condition prompt에 필요한 section이 없습니다: {heading}"
        )
    body = match.group("body").strip()
    if not body:
        raise ValueError(
            f"Governing condition prompt section 본문은 비어 있을 수 없습니다: {heading}"
        )
    return body


def _render_template(template: str, **values: str) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    missing = sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", rendered)))
    if missing:
        raise ValueError(
            f"Governing condition prompt 렌더링 값이 없습니다: {', '.join(missing)}"
        )
    return rendered
