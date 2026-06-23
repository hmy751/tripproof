# 2026-06-19 - Supabase 단일 retrieval 백엔드 경계와 server DX 정리

## 폴더 구성

- `index.md`: 결론과 현재 판단.
- `raw.md`: 이 결정에 이른 출발 직감, 거쳐온 교정, 논의 배경.

`raw.md`는 현재 실행 기준이 아니다. 다음 세션은 `index.md`를 먼저 읽고, 왜 이런 결정을 했는지 필요할 때만 `raw.md`를 본다.

> 업데이트: 2026-06-08 결정의 "첫 저장소는 in-memory로 둔다"를 대체한다. product retrieval은 Supabase 단일 경로로 두고, in-memory 구현은 테스트/eval 더블로만 남긴다.

## 맥락

이 결정은 server 코드 DX 정리 묶음의 결론이다. 정리는 두 갈래로 나뉜다. headline은 retrieval 백엔드 경계 결정이고, 그 결정을 끌어낸 것은 "분리가 제 값을 하는가"라는 일반 판단 기준이다. 이 기준이 같은 묶음의 dead code 제거, 이름 정정, 관심사 분리, 주석 추가를 함께 끌고 갔다.

retrieval에는 두 축이 섞여 있었다. 알고리즘 축(vector cosine ↔ lexical fallback)과 백엔드 축(누가 vector 검색을 수행하나)이다. 백엔드 축에는 `RetrievalRepository` 계약 아래 `InMemoryRetrievalRepository`(Python cosine)와 `SupabaseRetrievalRepository`(pgvector SQL) 두 구현이 있었고, `TRIPPROOF_RETRIEVAL_BACKEND`(기본 `memory`)가 둘을 전환했다.

그 결과 (1) cosine 유사도가 Python(`vector_math`)과 SQL RPC 두 곳에 중복으로 살았고, (2) 기본값이 `memory`라 product 기본 경로가 사실상 테스트용 in-memory 저장소였으며, (3) 같은 모양으로 answer composer에도 `ANSWER_COMPOSER_BACKEND`의 `disabled`/`missing` 분기가 있어, LLM을 끈 상태(테스트/eval 전용)를 product backend 값처럼 노출했다.

이 패턴을 일반화한 질문이 정리의 축이 됐다: 어떤 분리·계약·스위치가 product에서 제 값을 하는가, 아니면 모양만 갖춘 분리인가.

## 근거

### 분리는 모양이 아니라 정당성으로 판단한다 (earns-its-keep)

- 같은 계약의 두 구현이 있다는 사실 자체는 문제가 아니다. 문제는 그 분리가 product에서 제 값을 하는지다. 정당한 분리는 실제 확장 가능성, 테스트 주입 DX, 진짜 product 대안, 문서화된 계약 중 하나를 근거로 갖는다.
- 냄새는 그 근거가 없는데 나뉜 경우다: 테스트 scaffold를 product backend처럼 노출, 핵심 로직(cosine)을 두 곳에 손으로 복제, 단일 구현인데 미리 만든 추상, 값을 더하지 않는 forwarding.
- 이 기준으로 보면 `RetrievalRepository`/`LibraryChatAnswerComposer` 계약(Protocol)은 유지 가치가 있다. Ollama answer composer도 이후 provider 확장과 테스트 주입을 위해 정당하다. 반면 `RETRIEVAL_BACKEND` 스위치, in-memory를 product 선택지로 노출한 점, cosine 중복은 그 근거가 없다.
- 형식(모양)만으로 후보를 묶으면 정당한 분리(Ollama composer 계약)까지 냄새로 걸린다. 그래서 판정 기준은 모양이 아니라 정당성("왜 거기 있나")에 둔다.

### product 실행의 단일 진실

- product retrieval의 단일 진실은 Supabase다. in-memory 구현은 "또 다른 retrieval backend"가 아니라 무DB 테스트/로컬 대역이며, product config로 선택할 대상이 아니다.

## 결정

### Supabase 단일 retrieval 경계 (headline)

- product retrieval 백엔드는 Supabase 단일로 둔다. `TRIPPROOF_RETRIEVAL_BACKEND` env 스위치와 `RETRIEVAL_BACKEND` 상수를 제거한다.
- `InMemoryRetrievalRepository`와 Python `cosine_similarity`(`retrieval/vector_math.py`)를 product에서 제거하고 `apps/server/testing.py` 테스트 더블로 옮긴다. product 코드는 이 모듈을 import하지 않는다.
- `MaterialStore`는 `retrieval_repository`와 `retrieval_backend` 라벨을 명시로 받는다. 미사용 `MaterialStore.clear`와 `ClearableRetrievalRepository`를 제거한다.
- `create_app()`은 기본적으로 Supabase repository를 만든다. 테스트/eval은 `create_app(retrieval_repository=...)`로 in-memory 더블을 주입한다.
- answer composer의 `ANSWER_COMPOSER_BACKEND` `disabled`/`missing` 분기를 제거한다. `MissingLibraryChatAnswerComposer`(LLM 비활성 대역)도 `apps/server/testing.py`로 옮기고 테스트/eval이 직접 주입한다. product composer는 Ollama 단일이다.
- 관측 스냅샷의 `retrieval_backend`/`answer_model.backend` 라벨은 유지한다. 주입된 더블은 각각 `memory`/`missing`을 보고한다.

### 같은 기준으로 함께 정리한 server DX cleanup

위 earns-its-keep 기준을 server 전반에 적용한 결과다. 세부 변경은 commit과 `docs/work-log.md`에 있고, 여기서는 묶음만 남긴다.

- **호출자 0인 미사용 코드/scaffold 제거**: 미사용 `Fact` 모델, LLM client/types/providers 비계, checkin 프롬프트 자산, excerpt/select 스캐폴딩, no-trace `retrieve_context` wrapper, 미사용 observation exporter helper, `QuestionContextRetrievalResult` 등.
- **값을 더하지 않는 분기 라벨 제거**: `local_vector`/`SourceRetrievalStrategy` 라벨을 걷어내고 명시적 vector→lexical fallback 흐름으로 단순화.
- **오해를 부르는 이름 정정**: `fact_proposer` → `answer_composer`, `schemas/facts.py` → `schemas/evidence.py`(담는 것이 fact가 아니라 `EvidenceRefResponse` evidence 계약이라서).
- **관심사 분리(SoC)**: lexical 키워드 랭킹을 `retrieval/search.py`에서 `retrieval/lexical_ranking.py`로 분리. vector match와 lexical fallback이 한 파일에 섞여 있던 것을 읽기 단위로 가른다.
- **비자명한 why 주석(3종, 4곳)**: redaction allowlist의 silent-drop(두 observation 모듈에 동일 적용), time-answer gate, redaction-guard처럼 코드만 보면 의도가 안 보이는 지점에만 추가. 코드를 재진술하는 주석은 추가하지 않는다.

## 일반화한 판단 원칙

이 정리에서 다음 판단 기준을 정리했다. 다음 "구조를 더하거나 남길까" 결정의 기준으로 쓴다.

뿌리는 분리 자체가 아니라 판단 없는 보존·추가다 — 물려받은 흔적을 다시 판단하지 않고 보존하거나, 새 코드를 판단 없이 더하는 것. 이번 정리가 걷어낸 것도 대부분 이전 방식의 흔적(in-memory-first, local-vector, fact 시대 이름)을 다시 판단하지 않고 들고 온 경우였다. 좋은 분리(제 값을 하는 SoC·추상·계약)는 오히려 권장한다. 문제는 "나뉘었다"가 아니라 "왜 거기 있는지 아무도 판단하지 않았다"이다. 그래서 무언가를 더하거나 물려받은 것을 남기기 전에 "이게 제 값을 하는가"를 먼저 묻는다(earns-its-keep). 일관성(8)과 기준 적용(9) 축은 이 판단을 유지하고 과대적용을 막는 면이다.

### 분리의 정당성 (척추)

- **1.** 분리는 모양이 아니라 정당성으로 판단한다. 정당한 분리는 실제 확장, 테스트 주입, 진짜 product 대안, 문서화된 계약 중 하나를 근거로 갖는다. 근거 없는 분리(`RETRIEVAL_BACKEND` 스위치, cosine 중복)는 비용만 남긴다.
- **2.** (원칙 1을 노출 면에서 본 따름원칙) 이음새는 보존하되 그 선택을 product 스위치로 노출하지 않는다. Protocol(DI·확장 가치)은 유지하고, "어떤 구현을 쓸지"를 env 스위치로 빼지 않는다. 이음새를 두는 것과 선택을 노출하는 것은 다르다.
- **3.** SoC는 좋은 도구다. 무조건 적용하거나 무조건 의심하는 게 아니라, 그 분리가 지금 제 값을 할 때 적용한다. 읽기 단위를 가를 가치가 있으면 분리하고(`lexical_ranking` 분리가 그 예), 특정 지점에서 분리 비용(import cycle, 얽힌 실행 흐름)이 이득을 넘으면 그 자리만 보류한다. SoC를 의심하는 게 아니라 적용 시점을 판단하는 것이다.
- **4.** 죽은 코드는 호출자로 판정한다(YAGNI). 호출자가 0이면 제거하고 "나중에 쓸지도"로 남기지 않는다. 호출자 0(죽은 코드)과 호출자는 있으나 나눔이 값을 못 함(근거 없는 분리)을 구분한다.

### product 경계

- **5.** (원칙 1·2와 같은 in-memory 정리를 실행 진실 경로 면에서 본다) product에는 단일 진실 경로를 두고, 테스트 대역은 명시 주입 위치(`apps/server/testing.py`)에만 둔다. product가 무DB scaffold 위에서 무음으로 도는 기본값을 두지 않는다. 진짜 의존성이 없으면 조용히 도는 대신 명확히 실패한다.

### 이해 비용

- **6.** 이름은 담는 계약을 말한다. 이름과 내용이 어긋나면 정정한다(`facts.py`→`evidence.py`, `fact_proposer`→`answer_composer`). 어긋난 이름은 읽을 때마다 다시 해석하는 비용을 만든다.
- **7.** 주석은 코드로 드러나지 않는 "왜/의도"에만 단다. 코드를 재진술하는 주석은 잡음이며 그 자체가 가독성 저하다(이번 작업의 추가는 redaction silent-drop·time-answer gate·redaction-guard 4곳뿐).

### 일관성

- **8.** 코드에서 계약·설정 키를 바꾸면 그것을 가리키는 문서·template·spec·주석도 같은 커밋에서 정정한다. 코드와 문서는 같이 어긋난다(drift). 이번엔 `RETRIEVAL_BACKEND` 제거가 `.env.example`·spec(02/03/04)에 남긴 죽은 서술을 같은 묶음에서 정정했다.

### 메타 (기준을 적용하는 법)

- **9.** 형식 일치만으로 분리를 의심하면 과대 발동한다. 모양이 같다는 이유로 후보를 고르면 정당한 분리까지 걸리므로, "왜 거기 있나"라는 정당성으로 판정한다. 이 repo의 `2026-06-10` 결정과 같은 방향이다 — 증상을 탐지하기보다 결정 시점의 판단을 바꾼다.

## 기각 또는 보류

- in-memory를 product의 선택 가능한 백엔드로 유지하는 안: product 기본이 무DB scaffold로 동작하고 cosine 중복이 남아 기각.
- `RetrievalRepository`/`LibraryChatAnswerComposer` Protocol 제거: 확장성·테스트 주입 가치가 있어 유지.
- `retrieval/supabase.py`의 row↔model 매퍼 분리와 `observations/langsmith.py`의 payload 분리(SoC): `SupabaseRetrievalError` import cycle과 `_create_child_run_tree` interleave 때문에 깨끗한 분리 비용이 커 보류.
- `cards/` 서버 빈 placeholder 모듈: 서버 카드 계약이 아직 보류 상태이고 문서가 현재도 그 개념을 가리키므로 삭제하지 않고 유지.

## 검증

- `uv run pytest` (58 passed)
- `uv run black --check apps eval`
- Supabase 미설정 시 `create_app()`은 명확히 실패한다(무DB 무음 동작 금지). 테스트/eval은 placeholder 자격증명으로 import만 통과시키고 실제 연결은 하지 않는다.
- 코드 변경이 template/spec에 남긴 잔여 서술도 같은 묶음에서 정정했다. 두 갈래다: (1) 리팩토링(`local_vector`·strategy 라벨·`Fact` 타입 제거)으로 어긋난 spec 서술, (2) env 스위치 제거 후 `.env.example`의 죽은 키와 spec(02/03/04)의 잔여 스위치 서술. 여러 spec 파일에 걸친다(커밋 556d659/33726b5/4a45bb6).

## 이번 결정 밖

- 위 보류한 supabase row 매퍼·langsmith payload SoC 분리.
- production Supabase 운영 설정(URL/key 주입 경로, 마이그레이션).
- main 분기와의 병합 충돌(`observations/steps.py`, eval smoke) 해소.
