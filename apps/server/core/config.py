from __future__ import annotations

import os

ALLOWED_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

EMBEDDING_PROVIDER = os.getenv("TRIPPROOF_EMBEDDING_PROVIDER", "ollama")
EMBEDDING_MODEL = os.getenv("TRIPPROOF_EMBEDDING_MODEL", "nomic-embed-text-v2-moe")
EMBEDDING_DIMENSIONS = int(os.getenv("TRIPPROOF_EMBEDDING_DIMENSIONS", "768"))
EMBEDDING_AUTO_GENERATE = os.getenv("TRIPPROOF_EMBEDDING_AUTO_GENERATE", "0").lower() in {
    "1",
    "true",
    "yes",
}
OLLAMA_BASE_URL = os.getenv("TRIPPROOF_OLLAMA_BASE_URL", "http://localhost:11434")
