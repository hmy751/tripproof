# Source 영역

TripProof product code를 여기에 둔다.

`src/` 아래 코드는 사용자에게 보이는 흐름과 결과 계약을 가진다. 자료에서 확인한 정보, 근거, 불확실성, 충돌 상태를 표현한다.

product code는 root의 `eval/`, `fixtures/`, run artifact, metric output과 분리해서 유지한다.

## 구조

- `client/` — 사용자가 보는 TripProof React web app.
- `ai/` — Python AI 후보 생성 코드와 prompt/provider 자리. 최종 product contract가 아니라 server가 정규화할 후보 JSON을 만든다.
- `server/` — product entry point와 서버 내부 구현 자리.
- `server/trip-facts/` — 자료 후보를 `shared` 계약으로 정규화하는 TS server 경계.
- `shared/` — client와 server가 함께 읽는 결과 타입.
