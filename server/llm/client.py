from __future__ import annotations

from typing import Protocol


class StructuredOutputClient(Protocol):
    async def generate_structured(self, *, prompt: str, schema_name: str) -> object:
        """Return a provider-specific structured output payload."""
