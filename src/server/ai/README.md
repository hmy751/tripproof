# AI

AI 기능은 일단 server 내부 서비스로 둔다.

- `extractTripFacts.ts` — 자료에서 TripProof 결과 후보를 만드는 entry point.
- `normalizeTripFacts.ts` — 모델 결과를 저장 가능, 확인 필요, 근거 부족, 충돌 같은 product 상태로 정리한다.
- `prompts/` — 추출/근거 확인 prompt가 필요해지면 추가한다.
- `providers/` — OpenAI, local mock 같은 호출 구현이 필요해지면 추가한다.

client가 직접 LLM provider를 알지 않게 하고, server는 `shared`의 결과 계약으로만 값을 넘긴다.
