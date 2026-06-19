from __future__ import annotations

import os

import pytest

os.environ["TRIPPROOF_EMBEDDING_AUTO_GENERATE"] = "0"
# The import-time `app = create_app()` builds the Supabase-only production
# backend; tests never connect (they inject in-memory doubles), so placeholder
# credentials just let `server.app` import.
os.environ.setdefault("TRIPPROOF_SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("TRIPPROOF_SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")


@pytest.fixture(autouse=True)
def _stub_answer_composer(monkeypatch):
    """Default tests to the no-LLM composer so create_app() never hits Ollama.

    Production builds the Ollama composer; tests inject doubles instead. Tests
    that need a specific composer pass `library_chat_answer_composer=...` and
    override this default.
    """
    import server.app as server_app
    from server.testing import MissingLibraryChatAnswerComposer

    monkeypatch.setattr(
        server_app,
        "create_library_chat_answer_composer_from_config",
        lambda: MissingLibraryChatAnswerComposer(),
    )
