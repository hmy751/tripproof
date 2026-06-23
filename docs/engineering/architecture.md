# 아키텍처

현재 모듈 지도다. AI와 사람이 구조를 빠르게 파악하기 위한 것이지 희망 설계도가 아니다. 코드가 바뀌면 같이 고친다.

## 모듈 지도

- `apps/client` (React/Vite) — 사용자 UI. 서버에는 api 레이어로만 접근한다.
- `apps/server` (FastAPI) — 요청은 route → use_case → 아래 도메인·인프라로 흐른다.
  - route(`api`): HTTP 입출력 변환만.
  - use_case: 한 요청의 흐름을 조립.
  - 도메인: 자료 저장·수집(`materials`), 검색(`retrieval`), 근거 grounding(`extraction` — EvidenceState·EvidenceRef. 텍스트 추출 자체는 `materials/pdf`), 답변 합성(`answers`), 질문(`questions`).
  - 인프라: 프롬프트(`prompts`), LLM 클라이언트(`llm`), 스키마(`schemas`), 설정·에러(`core`), 실행 설정(`runtime`).
  - 관측: 내부 record와 외부 export(`observations`).
  - 아직 흐름이 없는 빈 scaffold는 지도에 넣지 않는다.
- `eval` — product를 밖에서 호출하는 관찰 계층. product 로직은 두지 않는다(경계는 아래).

## 의존 방향

- 의존은 한 방향으로만 흐른다: route → use_case → 하위. 하위(retrieval·extraction 등)에서 use_case나 route를 import하려는 순간이면 방향을 거스른 것이다.
- client → server는 api 레이어를 통해서만.
- eval → product 한 방향. product는 eval과 관측을 모른다.

## product / 관측 / eval 경계

- product: 사용자에게 보이는 흐름과 결과 계약.
- 관측(`observations`): 내부 record가 먼저, 외부 export는 그걸 소비하는 sink다. exporter가 꺼져도 product 응답은 같다.
- 한 요청을 client → server → 관측까지 같은 식별자로 꿴다. 사후에 한 흐름을 재구성하기 위해서다.
- 같은 코드라도 프롬프트·모델·설정이 바뀌면 동작이 바뀐다. 실행 설정은 스냅샷으로 남긴다.
- eval은 product를 관찰만 한다. product 로직을 eval에 중복하지 않고, product 응답이 eval에 의존하지 않는다.
- 제품 어휘·상태의 단일 기준은 `docs/product-model.md`다. 여기서 재서술하지 않는다.

## 조립 지점

- `create_app`은 외부 의존(store·repository·composer·exporter·sink·실행 설정)을 조립한다 — `principle.md`의 DIP가 실제로 사는 자리다. use_case 인스턴스는 route에서 요청별로 만들고, use_case 내부 협력자는 use_case가 직접 조립한다.
- 설정값 정의는 `core` 한 모듈에 모으되, 일부 기본값은 쓰는 쪽이 직접 읽는다.
