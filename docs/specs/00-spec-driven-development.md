# Spec-driven development structure

이 문서는 TripProof 구현을 시작하기 전에 어떤 spec 문서를 만들고, 어떤 문서는 나중으로 미룰지 정리한다.

상태: 계획 문서. 아직 product flow, eval run, before/after 결과가 있다는 뜻이 아니다. 이 문서는 spec을 어떻게 쓰는지 설명하는 기준이지, 현재 작업의 절차 gate나 queue가 아니다.

## 목표

TripProof의 spec은 기능 목록을 크게 적기 위한 문서가 아니라, 사용자가 보는 product flow를 작게 만들고 관찰하기 위한 기준이다.

첫 목표는 fixture나 eval runner를 먼저 완성하는 것이 아니라, 한 사용자 순간을 끝까지 통과시키는 것이다.

```text
자료 묶음
-> 필요한 fact 후보
-> 원문 근거
-> 근거 부족 또는 충돌 상태
-> 사용자 검수
-> 저장된 상황 카드 또는 사용자-facing 결과
-> 이 흐름에서 생긴 질문을 관찰
```

## 문서 경계

이 repo의 문서는 repo 안에서 독립적으로 읽혀야 한다. repo 밖의 개인 자료, 로컬 조사 경로, 대화 원문, 외부 지원 전략, 작업 도구 이름은 제품 문서의 근거처럼 노출하지 않는다.

문서에 남길 수 있는 것은 현재 repo에서 확인 가능한 목표, 제약, 결정, 열린 질문, 검증 후보다. 아직 구현되지 않은 product flow, eval run, before/after 결과는 완료된 것처럼 쓰지 않는다.

## Repo 문서 역할

| 영역 | 역할 |
| --- | --- |
| `docs/product-model.md` | 제품 어휘·상태·흐름의 단일 기준 문서. PRD/spec/README가 재서술 없이 참조 |
| `docs/roadmap/` | 후보 메뉴와 출발점 기록. 고정 계획·일정표·현재 작업 명령 아님 |
| `docs/specs/` | 여러 작업으로 이어지는 product behavior 기준 |
| `fixtures/` | synthetic 또는 sanitized sample material |
| `src/client/` | 사용자가 보는 product UI와 검수 상태 표현 |
| `src/server/` | product entry point와 서버 내부 구현 |
| `src/server/ai/` | 자료 추출, 근거 확인, LLM provider 연결 자리 |
| `src/shared/` | client와 server가 함께 읽는 결과 타입과 계약 |
| `eval/` | product behavior를 호출하고 관찰하는 코드와 기록 |
| `docs/decisions/` | 이후 구현 방향에 영향을 주는 선택 |
| `docs/work-log.md` | 중요한 작업의 얇은 재진입 기록 |

## 유지 기준

아래 기준은 구현 중 다시 미결처럼 흔들지 않는다.

- product가 먼저다. eval은 product behavior를 관찰한다.
- 코드 의존 방향은 `eval -> src`다. product code가 root의 `eval/`, fixture manifest, run artifact, metric output을 import하지 않는다.
- 첫 구현은 fixture/eval runner가 아니라 사용자 흐름 하나를 얇게 통과시킨다.
- 제품 화면과 문서의 첫 언어는 내부 평가 용어가 아니라 사용자의 행동 언어다.
- 작업 brief 수준의 가벼운 spec으로 시작한다.
- AI는 조사, 후보 생성, 구현 보조, 검증 보고를 맡을 수 있지만 채택/기각은 사람이 판단한다.
- eval 축 이름은 유지한다: Faithfulness/Groundedness, Citation Precision, Abstention F1, Conflict Recall.
- 큰 기술 후보는 baseline 실패가 보일 때만 비교 대상으로 연다.
- 공개 문장은 구현, run, proof 상태를 앞서가지 않는다.
- `src/product/` wrapper는 지금 만들지 않는다. 현재 구조는 `src/client`, `src/server`, `src/shared`의 물리적 경계로 product와 eval을 분리한다.

## 초기 문서 후보

초기 개발에 필요한 최소 spec 후보만 둔다. 아래 표는 현재 명령이 아니라, 같은 맥락을 다시 열 때 참고할 문서 역할이다. 제품 어휘·상태·흐름은 `docs/product-model.md` 기준 문서에서 한 번만 서술하고, 아래 문서들은 그 기준 문서를 참조한다.

| 문서 | 역할 | 완료 기준 |
| --- | --- | --- |
| `docs/product-model.md` | 제품 통합 모델 기준 문서(chat-first 흐름, 객체 모델, 상태 2축) | PRD/spec/README가 어휘·상태·흐름을 재서술하지 않고 이 기준 문서를 참조함 |
| `docs/prd.md` | TripProof의 제품 요구사항, 경계, 사용자 흐름, AI 동작 기준 | slice spec과 README가 같은 제품 기준을 참조할 수 있음 |
| `docs/specs/accommodation-checkin.md` | 첫 product slice의 목표, 입력/출력, acceptance, 열린 질문 | 첫 product contract와 fixture 설계를 시작할 만큼 명확함 |
| shared contract 메모 또는 타입 수정 | UI와 eval이 함께 읽을 최소 결과 구조가 필요할 때 참고 | fact, evidence, evidence state, sensitive 여부가 표현됨 |
| fixture case 자료 | product behavior 관찰이 필요할 때 참고 | product contract를 확인할 최소 case가 정리됨 |
| `docs/work-log.md` entry | 중요한 판단의 재진입 기록 | 왜 열었고 무엇이 남았는지 2-4줄로 남음 |

## 나중에 만들 문서

product flow가 실제로 생긴 뒤 만든다.

| 문서 | 여는 순간 |
| --- | --- |
| eval run summary | product entry point가 돌아가고 baseline을 관찰할 수 있을 때 |
| error analysis | 같은 실패가 반복되어 다음 product 수정 단위가 필요할 때 |
| decision note | 이후 구현 방향을 바꾸는 선택이 생겼을 때 |
| trace sharing policy | README나 demo에 trace 일부를 보여줄 때 |
| public case study | before, intervention, after, evidence가 모두 생긴 뒤 |

## 지금 만들지 않을 문서

아래 문서는 지금 만들면 실제 상태보다 앞서 보일 위험이 크다.

- 실제 run 없는 eval 결과표
- metric threshold 확정 문서
- graph, agent, tool architecture 도입 확정 문서
- OCR bbox citation 완료처럼 읽히는 문서
- PII taxonomy와 masking policy의 완성본
- 증거 없는 public before/after case study
- 작업량 메타를 product proof처럼 보이게 하는 운영 로그

## 첫 slice 선택

첫 slice는 `accommodation_checkin` moment로 둔다. 문서와 fixture directory 이름은 repo의 파일명 스타일에 맞춰 `accommodation-checkin`을 쓴다.

P0 기능은 `숙소 체크인 준비 확인`이다. 사용자는 예약 확인서와 호스트 안내를 넣고 체크인 시작 시간과 늦은 도착 조건을 확인한다.

이유:

- 사용자 순간이 분명하다.
- 자료 묶음이 작다.
- TripProof의 핵심인 fact 추출, 원문 근거, 근거 부족, 사용자 검수, 민감 정보 자동 저장 방지를 작게 확인할 수 있다.
- 투어, 렌터카, 여행 후 결제 검증으로 같은 contract를 확장하기 쉽다.

P0 관찰 case 후보는 happy path, missing late arrival, multi-doc supplement, conflict check-in time, sensitive guard다. 구현을 열 때는 현재 구조에 맞춰 `src/server/ai/extractTripFacts.ts`, `src/server/ai/normalizeTripFacts.ts`, `src/shared/tripFacts.ts`를 검토하고, 필요한 deterministic baseline만 둔다. LLM adapter는 P0 이후 별도 slice 후보로 남긴다. review UI는 현재 contract에 맞춰 조정할 수 있다.

## 최소 루프 감각

각 큰 작업은 product behavior를 먼저 닫기 위해 아래 감각을 참고한다. 이 목록은 문서 gate가 아니라 작업 brief를 작게 잡기 위한 힌트다.

- 왜 지금 이 slice를 여는가?
- 사용자가 실제로 할 수 있게 되는 동작은 무엇인가?
- product가 반환할 최소 구조는 무엇인가?
- 결과를 어떤 test 또는 수동 확인으로 관찰할 수 있는가?
- 채택, 기각, 보류, 남은 확인은 어디에 짧게 남길 것인가?

## Spec 품질 기준

좋은 spec:

- 사용자가 어떤 순간에 무엇을 확인하는지 보인다.
- 입력과 출력이 작다.
- 통과/실패가 product behavior로 관찰된다.
- 근거 부족과 충돌이 답변 실패가 아니라 제품 상태로 표현된다.
- 무엇을 지금 하지 않을지도 적혀 있다.

나쁜 spec:

- 기술명이 사용자 문제보다 먼저 나온다.
- 아직 없는 run 결과나 수치를 성과처럼 쓴다.
- fixture, eval, runner가 product보다 앞선다.
- 큰 후보를 모두 P0에 넣는다.
- repo 독자가 모르는 배경 설명이 제품 문장처럼 남는다.

## 열린 질문

- 민감 정보 masking을 `[masked]` 수준보다 정교하게 할 필요가 있는지.
- 직접 확인이 필요한 항목의 사용자 문구를 얼마나 강하게 경고형으로 표현할지.
- P0 이후 첫 확장은 LLM adapter, review UI, 실제 파일 ingestion 중 무엇으로 둘지.
- 첫 baseline run artifact를 언제 남길지.
