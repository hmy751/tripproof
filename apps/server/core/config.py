from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    repo_env_path = Path(__file__).resolve().parents[3] / ".env"
    env_paths = (repo_env_path, Path.cwd() / ".env")

    for env_path in dict.fromkeys(env_paths):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

ALLOWED_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]
CORS_EXPOSE_HEADERS = [
    "X-TripProof-Request-Id",
    "X-TripProof-Correlation-Id",
]
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

RETRIEVAL_BACKEND = os.getenv("TRIPPROOF_RETRIEVAL_BACKEND", "memory").lower()

EMBEDDING_PROVIDER = os.getenv("TRIPPROOF_EMBEDDING_PROVIDER", "ollama")
EMBEDDING_MODEL = os.getenv("TRIPPROOF_EMBEDDING_MODEL", "nomic-embed-text-v2-moe")
EMBEDDING_DIMENSIONS = int(os.getenv("TRIPPROOF_EMBEDDING_DIMENSIONS", "768"))
EMBEDDING_AUTO_GENERATE = os.getenv(
    "TRIPPROOF_EMBEDDING_AUTO_GENERATE", "1"
).lower() in {
    "1",
    "true",
    "yes",
}
OLLAMA_BASE_URL = os.getenv("TRIPPROOF_OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_TIMEOUT_SECONDS = float(
    os.getenv("TRIPPROOF_OLLAMA_EMBEDDING_TIMEOUT_SECONDS", "2.0")
)

FACT_PROPOSER_BACKEND = os.getenv("TRIPPROOF_FACT_PROPOSER_BACKEND", "ollama").lower()
OLLAMA_FACT_MODEL = os.getenv("TRIPPROOF_OLLAMA_FACT_MODEL", "gemma3:4b")
OLLAMA_FACT_TIMEOUT_SECONDS = float(
    os.getenv("TRIPPROOF_OLLAMA_FACT_TIMEOUT_SECONDS", "20.0")
)

RAG_TOP_K = int(os.getenv("TRIPPROOF_RAG_TOP_K", "3"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("TRIPPROOF_RAG_SIMILARITY_THRESHOLD", "0.0"))

OBSERVATION_EXPORT_DIR = os.getenv("TRIPPROOF_OBSERVATION_EXPORT_DIR", "").strip()
LANGSMITH_OBSERVATION_ENABLED = os.getenv(
    "TRIPPROOF_LANGSMITH_OBSERVATION_ENABLED",
    "",
).lower() in {"1", "true", "yes"}
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "").strip()
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "").strip()

SUPABASE_URL = os.getenv("TRIPPROOF_SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("TRIPPROOF_SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_INSERT_BATCH_SIZE = int(
    os.getenv("TRIPPROOF_SUPABASE_INSERT_BATCH_SIZE", "100")
)
SUPABASE_REST_TIMEOUT_SECONDS = float(
    os.getenv("TRIPPROOF_SUPABASE_REST_TIMEOUT_SECONDS", "6.0")
)
