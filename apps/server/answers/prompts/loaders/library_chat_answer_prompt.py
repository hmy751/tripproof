from __future__ import annotations

from server.answers.prompts.loaders.llm_prompt_file_loader import load_llm_prompt
from server.answers.prompts.loaders.markdown_prompt_asset import PromptAsset


LIBRARY_CHAT_PROMPT_NAME = "library_chat_answer"
LIBRARY_CHAT_PROMPT_VERSION = "2026-06-10"


def load_library_chat_prompt(version: str = LIBRARY_CHAT_PROMPT_VERSION) -> PromptAsset:
    return load_llm_prompt(
        name=LIBRARY_CHAT_PROMPT_NAME,
        version=version,
        required_sections=("System", "User"),
        required_placeholders=("question", "source_blocks"),
    )
