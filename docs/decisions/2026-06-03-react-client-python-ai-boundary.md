# React client와 Python AI 경계

> 상태: 2026-06-08 `docs/decisions/2026-06-08-python-backend-uv-ingest-boundary.md` 결정으로 대체됨. 현재 구현은 `apps/client/`, `apps/server/`, `uv` lockfile을 기준으로 하며, `src/ai`, `src/server/trip-facts`, `src/shared`는 삭제했다.

## 결정

client는 React/Vite web app으로 전환한다. 기존 정적 화면의 상단 상태, 자료함 sidebar, 확인 탭, 원문 근거 표, 저장 카드 흐름은 버리지 않고 React state로 옮긴다.

AI 쪽은 Python 패키지를 `src/ai/`에 새로 둔다. prompt/provider adapter도 AI 후보 생성 내부 구현이므로 `src/ai/` 아래에 둔다. Python은 최종 `TripProofResult`를 소유하지 않고 `RawTripFactCandidate` 모양의 후보 JSON을 만든다. TypeScript `src/server/trip-facts/normalizeTripFacts.ts`가 후보를 `src/shared/tripFacts.ts`의 product contract로 정규화한다.

## 이유

- 브라우저와 TS server가 함께 읽는 계약은 지금 `src/shared/tripFacts.ts`가 가장 가까운 source of truth다.
- Python이 TS 파일을 직접 import할 수는 없으므로 언어 경계는 JSON으로 둔다.
- `src/server/ai`라는 이름은 prompt/provider까지 server에 있어야 하는 것처럼 읽히므로, server 쪽은 `src/server/trip-facts`로 좁혀 부른다.
- Python/Pydantic을 최종 product contract의 주인으로 올리면 client/server/eval 경계가 한 번에 커진다.
- 현재 product 흐름은 아직 숙소 체크인 baseline을 통과시키는 단계라, LLM adapter나 full ingestion보다 후보 생성 경계를 먼저 얇게 잡는 편이 안전하다.

## 보류

- `src/product/` wrapper는 만들지 않는다.
- 카드 출처와 `ReviewDecision`은 아직 `shared`로 승격하지 않고 client local state로 둔다.
- 실제 PDF/OCR/LLM 호출은 baseline 실패가 보일 때 별도 slice로 연다.
