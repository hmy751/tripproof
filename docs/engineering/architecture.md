# 아키텍처

현재 모듈 지도다. AI와 사람이 구조를 빠르게 파악하기 위한 것이지 희망 설계도가 아니다. 코드가 바뀌면 같이 고친다.

## 모듈 지도

- `apps/client` (React/Vite) — 사용자 UI. 서버에는 api 레이어로만 접근한다.
- `apps/server` (FastAPI) — route → use_case → retrieval / extraction / answers / materials.
  - route: HTTP 입출력 변환만.
  - use_case: 한 요청의 흐름을 조립.
  - 그 아래: 검색, 추출, 답변 합성, 자료 저장(materials).
- `eval` — product를 밖에서 호출해 동작을 관찰한다. product 로직은 두지 않는다.

## 의존 방향

- 의존은 한 방향으로만 흐른다: route → use_case → 하위. 위로 거슬러 의존하지 않는다.
- client → server는 api 레이어를 통해서만.
- eval → product 한 방향. product는 eval과 관측을 모른다.

## product / 관측 / eval 경계

- product: 사용자에게 보이는 흐름과 결과 계약.
- 관측: 내부 record가 먼저, 외부 export는 그걸 소비하는 sink다. exporter가 꺼져도 product 응답은 같다.
- eval: product를 관찰만 한다. product 로직을 중복하지 않고, product 응답이 eval에 의존하지 않는다.
- 제품 어휘·상태의 단일 기준은 `docs/product-model.md`다. 여기서 재서술하지 않는다.

## 조립 지점

- `create_app`이 의존성을 한곳에서 조립한다. 설정·환경값은 한 모듈에 모은다.
