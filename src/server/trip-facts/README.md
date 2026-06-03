# Trip Facts Server Boundary

이 폴더는 TypeScript server boundary다. Python AI나 deterministic baseline이 만든 후보를 최종 product result로 정규화한다.

- `extractTripFacts.ts` — 자료에서 TripProof 결과 후보를 만드는 entry point.
- `normalizeTripFacts.ts` — 모델 결과를 저장 가능, 확인 필요, 근거 부족, 충돌 같은 product 상태로 정리한다.

client가 직접 LLM provider를 알지 않게 하고, server는 `shared`의 결과 계약으로만 값을 넘긴다.

Python AI 코드는 `src/ai/`에 둔다. Python은 `RawTripFactCandidate` 형태의 후보 JSON을 만들고, 이 폴더의 TypeScript 코드가 `TripProofResult`로 정규화한다.
