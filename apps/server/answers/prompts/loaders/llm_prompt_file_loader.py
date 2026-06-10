from __future__ import annotations

from pathlib import Path

from server.answers.prompts.loaders.markdown_prompt_asset import PromptAsset, load_markdown_prompt_asset


PROMPT_ROOT = Path(__file__).resolve().parents[1]
LLM_PROMPT_ROOT = PROMPT_ROOT / "llm"


def load_llm_prompt(
    *,
    name: str,
    version: str,
    required_sections: tuple[str, ...] = (),
    required_placeholders: tuple[str, ...] = (),
) -> PromptAsset:
    path = LLM_PROMPT_ROOT / name / f"{version}.md"
    asset_path = f"apps/server/answers/prompts/llm/{name}/{version}.md"
    return load_markdown_prompt_asset(
        category="llm",
        name=name,
        version=version,
        path=path,
        asset_path=asset_path,
        required_sections=required_sections,
        required_placeholders=required_placeholders,
    )
