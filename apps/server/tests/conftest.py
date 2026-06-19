from __future__ import annotations

import os

os.environ["TRIPPROOF_RETRIEVAL_BACKEND"] = "memory"
os.environ["TRIPPROOF_EMBEDDING_AUTO_GENERATE"] = "0"
os.environ["TRIPPROOF_ANSWER_COMPOSER_BACKEND"] = "missing"
