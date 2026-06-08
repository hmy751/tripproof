# TripProof

TripProof는 여행자가 받은 예약, 일정, 안내 자료를 행동하기 전에 확인할 수 있도록 돕는 초기 제품 실험이다.

여행 자료에는 항공편 시간, 숙소 주소, 체크인 조건, 취소 규정처럼 행동 전에 다시 확인해야 하는 정보가 흩어져 있다. TripProof는 이런 자료에서 핵심 정보를 찾아 원문 근거와 함께 보여주고, 확인할 수 없는 내용이나 서로 충돌하는 내용은 무리해서 단정하지 않는다.

## 현재 상태

이 repo는 초기 구현 단계다. 아직 완성된 제품 흐름이나 평가 결과를 전제로 하지 않는다.

## 제품 방향

- 여행자가 받은 자료에서 확인해야 할 정보를 정리한다.
- 각 정보가 어디에서 왔는지 원문 근거를 함께 보여준다.
- 근거가 부족하거나 자료끼리 충돌하면 그 상태를 드러낸다.

## Repo 구조

- `apps/client/` — 사용자에게 보이는 React/Vite product UI.
- `apps/server/` — Python/FastAPI backend. API route, 자료 ingest, retrieval, extraction, LLM adapter, card logic을 이 아래에 둔다.
- `fixtures/` — 안전한 샘플 자료.
- `eval/` — product behavior를 관찰하는 평가 코드와 기록.
- `docs/` — 필요한 설계 메모와 결정 기록.

## 문서 역할

- `CLAUDE.md` / `AGENTS.md` — 항상 켜지는 로컬 실행 경계. 제품 세부 spec이나 과거 분석을 담지 않는다.
- `docs/product-model.md` — 제품 어휘·상태·흐름의 단일 기준. 구현 순서나 다음 작업 queue가 아니다.
- `docs/prd.md` — 제품 요구사항과 경계.
- `docs/specs/` — 여러 작업에 다시 쓰일 product behavior acceptance. 현재 작업에 필요한 spec만 읽는다.
- `docs/roadmap/` — 후보 메뉴와 출발점 기록. 일정표나 다음 명령이 아니다.
- `docs/work-log.md` — 과거 작업의 얇은 재진입 기록. 여기의 후보는 현재 실행 지시가 아니다.
- `docs/decisions/` — 이후 구현 방향에 영향을 주는 선택 기록. decision note 하나가 전체 문서 개편 승인을 뜻하지 않는다.
- `docs/archive/` — 동결 스냅샷·참조 보관소. 활성 문서가 아니며 갱신하지 않는다.

## 로컬 실행

Node는 최신 LTS를 기준으로 맞춘다. Python backend는 `uv`로 의존성과 가상환경을 관리한다.

```sh
nvm use
npm install
uv sync
```

backend와 client는 각각 실행한다.

```sh
npm run backend:dev
npm run dev
```

검증:

```sh
npm run build
npm run backend:test
```
