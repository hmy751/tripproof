# 2026-06-19 - Supabase 단일 retrieval 백엔드 경계

> 업데이트: 2026-06-08 결정의 "첫 저장소는 in-memory로 둔다"를 대체한다. product retrieval은 Supabase 단일 경로로 두고, in-memory 구현은 테스트/eval 더블로만 남긴다.

## 맥락

retrieval에는 두 축이 섞여 있었다. 알고리즘 축(vector cosine ↔ lexical fallback)과 백엔드 축(누가 vector 검색을 수행하나)이다. 백엔드 축에는 `RetrievalRepository` 계약 아래 `InMemoryRetrievalRepository`(Python cosine)와 `SupabaseRetrievalRepository`(pgvector SQL) 두 구현이 있었고, `TRIPPROOF_RETRIEVAL_BACKEND`(기본 `memory`)가 둘을 전환했다.

그 결과 (1) cosine 유사도가 Python(`vector_math`)과 SQL RPC 두 곳에 중복으로 살았고, (2) 기본값이 `memory`라 product 기본 경로가 사실상 테스트용 in-memory 저장소였으며, (3) 같은 모양으로 answer composer에도 `ANSWER_COMPOSER_BACKEND`의 `disabled`/`missing` 분기가 있어, LLM을 끈 상태(테스트/eval 전용)를 product backend 값처럼 노출했다.

## 근거

- product 실행의 단일 진실은 Supabase다. in-memory 구현은 "또 다른 retrieval backend"가 아니라 무DB 테스트/로컬 대역이며, product config로 선택할 대상이 아니다.
- 같은 계약의 두 구현 자체는 문제가 아니다. 문제는 그 구현 선택을 product env 스위치로 노출해 테스트 scaffold를 product backend처럼 보이게 한 점과, cosine 핵심 로직을 손으로 동기화하는 중복이었다.
- `RetrievalRepository`/`LibraryChatAnswerComposer` 계약(Protocol)은 확장성과 테스트 주입 가치가 있으므로 유지한다. 테스트 더블은 product 모듈이 아니라 명시 주입되는 위치에 둔다.

## 결정

- product retrieval 백엔드는 Supabase 단일로 둔다. `TRIPPROOF_RETRIEVAL_BACKEND` env 스위치와 `RETRIEVAL_BACKEND` 상수를 제거한다.
- `InMemoryRetrievalRepository`와 Python `cosine_similarity`(`retrieval/vector_math.py`)를 product에서 제거하고 `apps/server/testing.py` 테스트 더블로 옮긴다. product 코드는 이 모듈을 import하지 않는다.
- `MaterialStore`는 `retrieval_repository`와 `retrieval_backend` 라벨을 명시로 받는다. 미사용 `MaterialStore.clear`와 `ClearableRetrievalRepository`를 제거한다.
- `create_app()`은 기본적으로 Supabase repository를 만든다. 테스트/eval은 `create_app(retrieval_repository=...)`로 in-memory 더블을 주입한다.
- answer composer의 `ANSWER_COMPOSER_BACKEND` `disabled`/`missing` 분기를 제거한다. `MissingLibraryChatAnswerComposer`(LLM 비활성 대역)도 `apps/server/testing.py`로 옮기고 테스트/eval이 직접 주입한다. product composer는 Ollama 단일이다.
- 관측 스냅샷의 `retrieval_backend`/`answer_model.backend` 라벨은 유지한다. 주입된 더블은 각각 `memory`/`missing`을 보고한다.

## 기각 또는 보류

- in-memory를 product의 선택 가능한 백엔드로 유지하는 안: product 기본이 무DB scaffold로 동작하고 cosine 중복이 남아 기각.
- `RetrievalRepository`/`LibraryChatAnswerComposer` Protocol 제거: 확장성·테스트 주입 가치가 있어 유지.
- `retrieval/supabase.py`의 row↔model 매퍼 분리와 `observations/langsmith.py`의 payload 분리(SoC): `SupabaseRetrievalError` import cycle과 `_create_child_run_tree` interleave 때문에 깨끗한 분리 비용이 커 보류.
- `cards/` 서버 빈 placeholder 모듈: 서버 카드 계약이 아직 보류 상태이고 문서가 현재도 그 개념을 가리키므로 삭제하지 않고 유지.

## 검증

- `uv run pytest` (58 passed)
- `uv run black --check apps eval`
- Supabase 미설정 시 `create_app()`은 명확히 실패한다(무DB 무음 동작 금지). 테스트/eval은 placeholder 자격증명으로 import만 통과시키고 실제 연결은 하지 않는다.

## 이번 결정 밖

- 위 보류한 supabase row 매퍼·langsmith payload SoC 분리.
- production Supabase 운영 설정(URL/key 주입 경로, 마이그레이션).
- main 분기와의 병합 충돌(`observations/steps.py`, eval smoke) 해소.
