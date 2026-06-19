# Raw Notes - Supabase 단일 retrieval 백엔드 경계와 server DX 정리

이 파일은 `index.md` 결정의 배경 재료이며, 거쳐온 문제 감각과 교정을 보존하기 위한 자료다. 현재 실행 기준이나 작업 대기열이 아니다. 결론은 `index.md`에 있고, 여기 후보·표현을 현재 작업으로 쓰려면 `index.md`와 현재 코드 상태로 다시 판단한다.

## 왜 raw가 필요한가

이 정리의 핵심은 "무엇을 지웠나"보다 "어떤 분리를 의심하게 됐고, 그 의심의 기준이 어떻게 날카로워졌나"다. 출발 기준은 거칠었고 두 번 교정됐다. 그 교정 과정을 남겨야 다음에 "이 분리를 둘까 말까"를 다시 만났을 때 같은 출발점을 헤매지 않는다.

## 출발 직감

작업은 코드 품질·DX 쪽 직감에서 출발했다.

1. **관심사 분리(SoC)가 DX를 높인다.** 한 파일/한 함수가 섞어 든 책임을 읽기 단위로 가르면 관리가 쉬워진다고 봤다.
2. **비자명한 곳에 why 주석을 더하고 싶다.** 단 가독성·관리가 더러워지면 안 된다. 코드를 재진술하는 주석은 늘리지 않는다.
3. **외부 레퍼런스 축으로도 본다.** 주석·분리 판단을 직관이 아니라 정착된 엔지니어링 기준에 비춘다.

처음에는 이 직감으로 dead code·이름·구조를 정리했다(초기 묶음: 답변 읽기 흐름 정렬과 evidence grounding 분리, 미사용 Fact 모델·LLM client 비계·checkin 프롬프트 자산 제거, `fact_proposer`→`answer_composer` 네이밍, excerpt/select 스캐폴딩과 ranker 단순화, `local_vector`·`SourceRetrievalStrategy` 라벨 제거).

## 거쳐온 교정

- **모순 자각이 기준을 날카롭게 했다.** retrieval 백엔드를 "전략처럼 대체제가 없다"고 설명하던 중에, 같은 자리에 Supabase라는 명백한 대체 구현이 이미 있었다. 이 모순이 "그럼 in-memory는 product 백엔드인가, 테스트 대역인가"를 강제로 물게 했다. 답은 후자였고, in-memory는 제거 대상이 됐다.
- **첫 전수 점검은 형식(shape)으로 봤다.** "같은 모양의 분기/env 스위치"를 모두 같은 냄새로 묶었더니, 실제로는 정당한 분리인 Ollama answer composer 계약까지 후보로 잡혔다.
- **기준을 모양에서 정당성으로 바꿨다(earns-its-keep).** Ollama composer는 이후 provider 확장과 테스트 주입을 위해 필요하고 DX상으로도 정당하다. 문제는 in-memory처럼 근거 없이 product 경계에 나뉜 분리다. 이 기준으로 전수 점검을 다시 돌려 후보를 다시 골랐다.
- **테스트 대역이 product 경계에 어중간하게 남아 있던 것을 정리했다.** LLM 비활성 대역(`MissingLibraryChatAnswerComposer`)이 왜 product 경계에 남았는지 의심이 들어 호출자를 역추적했고, product 호출자가 없는 테스트/eval 전용 더블임이 확인됐다. 그래서 in-memory 더블과 함께 명시 주입 위치(`apps/server/testing.py`)로 옮겼다.

## 주석 정책의 근거 (외부 레퍼런스)

세 번째 직감(외부 기준)을 주석에 적용할 때 다음 원칙을 따랐다.

- 비자명한 것에만 주석을 단다. 코드가 이미 말하는 것을 다시 말하는 주석은 잡음이고, 그 자체가 더러움이다.
- 주석은 "어떻게"가 아니라 "왜"와 추상(의도·계약)을 적는다.
- 인터페이스 주석(무엇을 보장하나)과 구현 주석(왜 이렇게 했나)을 구분한다.

근거로는 소프트웨어 설계서 *A Philosophy of Software Design*의 "주석은 코드로 표현 안 되는 의도를 담는다" 관점과, 대형 엔지니어링 조직의 코드리뷰 관행(설명이 필요한 비자명한 지점에만 주석)을 참고했다. 실제 추가는 redaction allowlist의 silent-drop 의도, time-answer gate, redaction-guard 세 종뿐이다(allowlist 주석은 두 observation 모듈에 동일 적용해 물리적으로 네 곳).

## 출처와 확인된 사실 (당시 코드 기준)

- in-memory 구현은 단순 cosine 계산기가 아니라 무DB **storage 백엔드**였다(`store.retrieval_records` → `repository.records_for_materials`). 그래서 제거하면 Supabase가 product에서 필수가 된다.
- product 코드는 `apps/server/testing.py`를 import하지 않는다. 더블은 테스트/eval에서만 주입된다.
- LLM 비활성 composer 대역은 product 호출자가 0이었고, 저장소 문서에서도 stub은 테스트 더블로 명시돼 있었다.
- 코드를 바꿨을 때 template와 spec에 잔여 서술이 남는 drift가 실제로 발생했다(별도 전수 점검에서 확인). 두 갈래를 같은 묶음에서 정정했다: 리팩토링(`local_vector`·strategy 라벨·`Fact` 타입 제거)으로 어긋난 spec 서술, 그리고 env 스위치 제거 후 `.env.example`의 죽은 키와 spec(02/03/04)의 잔여 스위치 서술. 여러 spec 파일에 걸친다.
- 검증 기준: `uv run pytest`(58 passed), `uv run black --check apps eval`. Supabase 미설정 시 `create_app()`은 명확히 실패하고, 테스트/eval은 placeholder 자격증명으로 import만 통과시킨다(실제 연결 없음).

## 기각·보류된 후보 (현재 후보 아님)

- in-memory를 product 선택지 백엔드로 유지 — 기각.
- `RetrievalRepository`/`LibraryChatAnswerComposer` Protocol 제거 — 기각(확장·테스트 주입 가치).
- `retrieval/supabase.py` row↔model 매퍼 분리, `observations/langsmith.py` payload 분리 — 보류(import cycle, child run interleave로 분리 비용 큼).
- `cards/` 서버 placeholder 제거 — 보류(서버 카드 계약 미정, 문서가 아직 개념을 가리킴).

## 남은 불확실성

- earns-its-keep 기준이 다음 "분리를 둘까 말까" 결정에서 실제로 결정 시점 attention을 바꾸는지는 다음 작업에서 관찰해야 확인된다.
- 보류한 두 SoC 분리(supabase row 매퍼, langsmith payload)의 비용/이득은 다시 평가해야 한다.
- 서버 카드 계약을 언제 닫을지(또는 placeholder를 언제 정리할지).

## 재진입 메모

- 새 백엔드·분기·env 스위치를 추가하려 할 때, 코드를 짜기 전에 한 줄로 답한다: 이 분리가 제 값을 하나(실제 확장 / 테스트 주입 / 진짜 product 대안 / 문서화된 계약 중 하나의 근거가 있나), 아니면 모양만인가.
- config 키를 코드에서 지우면 template(`.env.example`)·spec·주석의 잔여 서술도 같은 커밋에서 정리한다.
- 테스트/eval 대역은 product 모듈 경계가 아니라 명시 주입 위치(`apps/server/testing.py`)에 둔다.
