from __future__ import annotations

from pathlib import Path

from server.prompts.runtime.prompt_document import PromptDocument, read_prompt_document

PROMPT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_ASSET_ROOT = PROMPT_ROOT / "assets"


def load_prompt_document(*, domain: str, name: str, version: str) -> PromptDocument:
    path = PROMPT_ASSET_ROOT / domain / name / f"{version}.md"
    asset_path = f"apps/server/prompts/assets/{domain}/{name}/{version}.md"
    return read_prompt_document(
        domain=domain,
        name=name,
        version=version,
        path=path,
        asset_path=asset_path,
    )
