# Source 영역

TripProof product code를 여기에 둔다.

`src/` 아래 코드는 사용자에게 보이는 흐름과 결과 계약을 가진다. 자료에서 확인한 정보, 근거, 불확실성, 충돌 상태를 표현한다.

product code는 root의 `eval/`, `fixtures/`, run artifact, metric output과 분리해서 유지한다.

## 구조

- `client/` — 사용자가 보는 TripProof UI. 현재는 브라우저에서 바로 열 수 있는 정적 뼈대다.
- `server/` — product entry point와 서버 내부 구현 자리.
- `server/ai/` — 자료 추출, 근거 확인, LLM provider 연결 자리.
- `shared/` — client와 server가 함께 읽는 결과 타입.
