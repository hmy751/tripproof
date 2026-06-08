# Source 영역

TripProof product code를 여기에 둔다.

`src/` 아래 코드는 사용자에게 보이는 흐름과 결과 계약을 가진다. 자료에서 확인한 정보, 근거, 불확실성, 충돌 상태를 표현한다.

product code는 root의 `eval/`, `fixtures/`, run artifact, metric output과 분리해서 유지한다.

## 구조

- `client/` — 사용자가 보는 TripProof React web app.

Python backend는 repo root의 `server/`에 둔다. `src/` 아래에는 browser client code만 남긴다.
