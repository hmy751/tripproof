from __future__ import annotations

import json
import sys

from .baseline import extract_candidates
from .models import CandidateEnvelope


def main() -> int:
    payload = json.load(sys.stdin)
    envelope = CandidateEnvelope.from_dict(payload)
    candidates = extract_candidates(envelope)
    json.dump(
        {"candidates": [candidate.to_dict() for candidate in candidates]},
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
