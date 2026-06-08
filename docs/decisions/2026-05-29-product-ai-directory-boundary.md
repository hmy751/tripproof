# 2026-05-29 - Product와 AI 디렉토리 경계

> 상태: 2026-06-08 `docs/decisions/2026-06-08-python-backend-uv-ingest-boundary.md` 결정으로 대체됨. 현재 구조는 `apps/client/`와 `apps/server/`를 기준으로 한다.

## 맥락

TripProof는 AI 기능을 붙이는 초기 product 실험이다. 이전 작업에서 eval code, fixture, run artifact, metric output이 product code로 스며들면 제품 흐름이 오염될 수 있다는 문제가 있었다.

그래서 repo의 큰 경계는 `src/`의 product code와 root의 `eval/`을 분리하는 product-first 구조를 유지한다.

## 결정

현재 단계에서는 `src/` 바로 아래에 client, server, shared를 둔다.

```txt
src/
  client/
  server/
    ai/
  shared/
```

`src/client/`는 사용자가 보는 UI를 둔다. `src/server/`는 product entry point와 서버 내부 구현을 둔다. `src/server/ai/`는 LLM, prompt, provider, extraction workflow처럼 서버에서 실행되는 AI 기능을 둔다. `src/shared/`는 client와 server가 함께 읽는 결과 타입과 계약을 둔다.

AI 관련 product logic은 일단 `server/ai` 안에서 파일 단위로 나눈다.

```txt
src/server/ai/
  extractTripFacts.ts
  normalizeTripFacts.ts
  prompts/
  providers/
```

`extractTripFacts.ts`는 자료에서 후보 정보와 근거를 찾는 workflow를 맡는다. `normalizeTripFacts.ts`는 모델 결과를 저장 가능, 확인 필요, 근거 부족, 충돌 같은 product 상태로 정리하는 규칙을 맡는다.

## 기각 또는 보류

`src/core/`는 지금 만들지 않는다.

core 개념은 모델 결과를 제품 규칙으로 해석하는 역할로 유효하지만, 현재는 구현이 작고 구분 비용이 더 크다. 지금 core를 만들면 `core`와 `server/ai` 경계를 계속 설명해야 해서 구조가 먼저 일을 만들 수 있다.

나중에 `normalizeTripFacts.ts` 같은 규칙 파일이 커지고, AI provider 없이도 독립 테스트하거나 client/eval이 같은 규칙을 직접 참조해야 하면 그때 `src/core/` 같은 분리를 다시 판단한다.

`src/product/` wrapper는 지금 쓰지 않는다. product와 eval의 경계는 `src/product/` 이름이 아니라 `src/`와 root `eval/`의 물리적 분리로 드러낸다.

## 검증

비슷한 제품형 AI 프로젝트 구조를 비교했다. 그 사례는 `app/`과 `evals/`, `experiments/`를 분리하고, 모델 호출과 검색/선별/방어 규칙이 `app/` 내부에 함께 존재한다. TripProof도 같은 문제의식을 따른다.

다만 TripProof는 초기 단계라 세부 레이어를 많이 만들지 않고, product-first 경계만 유지한다.

## 다음

- `server/ai` 안의 파일이 커지기 전까지는 현재 구조를 유지한다.
- eval은 product entry point를 호출해서 관찰하되, product가 eval fixture, run artifact, metric output에 의존하지 않게 둔다.
- 모델 호출과 product 규칙이 한 파일에서 읽기 어려워지면 `normalizeTripFacts.ts`를 먼저 분리한다.
- `normalizeTripFacts.ts`가 AI provider와 무관한 순수 규칙으로 커지면 `src/core/` 같은 분리를 다시 판단한다.
