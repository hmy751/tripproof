# Accommodation check-in slice

상태: 첫 product slice의 P0 기능 기준. 아직 구현 완료나 eval 결과를 뜻하지 않는다.

제품 전체의 요구사항과 경계는 `../prd.md`를 기준으로 한다. 이 문서는 그중 첫 slice인 숙소 체크인 확인만 다룬다.

## 기능 결정

P0 기능은 `숙소 체크인 준비 확인`으로 고정한다.

사용자는 숙소 체크인 직전에 예약 확인서와 호스트 안내를 넣고, 아래 두 가지를 확인한다.

- 체크인은 언제부터 가능한가?
- 늦게 도착하면 무엇을 해야 하는가?

TripProof는 이 질문에 대해 자유 대화 답변을 만들지 않는다. 자료에서 확인 가능한 fact 후보를 만들고, 각 후보에 원문 근거와 상태를 붙인다. 사용자가 저장한 fact만 최종 체크인 카드에 표시한다.

이 기능의 본질은 "숙소 체크인 정보를 요약한다"가 아니라 "행동 전에 믿어도 되는 정보와 아직 믿으면 안 되는 정보를 근거와 함께 분리한다"는 것이다.

## 목표

여행자가 숙소 체크인 전 받은 자료에서 체크인 시간과 늦은 도착 조건을 원문 근거와 함께 확인한다.

TripProof는 자료에 없는 내용을 일반 지식으로 보충하지 않는다. 민감하거나 애매한 값은 자동 저장하지 않고 사용자가 확인할 수 있게 남긴다.

## 왜 이 slice인가

숙소 체크인은 여행자가 압박 있는 순간에 확인해야 하는 정보가 작고 분명하다.

- 체크인 시간
- 늦은 도착 조건
- 예약번호 필요 여부
- 출입 방법 또는 self check-in 조건

이 slice는 TripProof의 핵심 동작을 사용자 장면 안에서 작게 포함한다.

- 필요한 fact를 뽑는다.
- fact마다 원문 근거를 붙인다.
- 근거가 부족하면 멈춘다.
- 사용자가 저장, 수정, 무시한다.
- 저장된 fact만 상황 카드에 표시한다.

## 사용자 시나리오

사용자는 숙소 근처에 있거나 이동 중이다. 예약 확인서와 호스트 체크인 안내를 가지고 있고, 지금 확인해야 할 것은 다음이다.

> 체크인은 몇 시부터 가능하고, 늦게 도착하면 무엇을 해야 하지?

## P0 범위

### 포함

P0에서 끝까지 구현할 field는 아래 두 개다.

| Field id | 사용자 문구 | 기대 값 | P0 상태 |
| --- | --- | --- | --- |
| `check_in_start_time` | 체크인 시작 시간 | `3:00 PM`, `15:00`, `오후 3시 이후` 같은 자료 기반 값 | 필수 |
| `late_arrival_instruction` | 늦은 도착 조건 | `22:00 이후 도착 시 사전에 숙소에 연락` 같은 행동 가능한 조건 | 필수 |

P0에서 반드시 표현할 evidence state는 현재 `src/shared/tripFacts.ts`의 `EvidenceState`를 기준으로 한다.

| EvidenceState | 사용자 문구 | 의미 | P0에서 필요한 이유 |
| --- | --- | --- | --- |
| `supported` | 확인됨 | 자료 근거로 확인됨 | 정상 확인 결과를 표현한다. |
| `missing` | 근거 부족 | 자료에 근거가 부족함 | 자료에 없는 내용을 만들어내지 않는다. |
| `conflict` | 자료 충돌 | 자료끼리 다른 값을 말함 | 서로 다른 체크인 시간을 하나로 합치지 않는다. |
| `needs_review` | 확인 필요 또는 직접 확인 | 사용자가 직접 확인해야 함 | 민감하거나 자동 확정하면 위험한 값을 저장하지 않는다. |

별도 `manual_check` status는 지금 만들지 않는다. P0에서는 `needs_review`와 `sensitive: true`, `openIssues` 문구로 직접 확인이 필요한 상태를 표현한다.

### 제외

P0에서는 아래를 구현하지 않는다.

- 실제 PDF, 이미지, 이메일 ingestion
- OCR 영역 표시
- open-ended Q&A
- 예약번호 필요 여부의 정교한 판단
- 출입 방법 전체 추출
- 출입 코드, 연락처, 결제 정보의 원문 값 저장
- 다국어 일반화
- timezone 정규화
- 실제 품질 metric 계산

단, 자료 안에 예약번호, 출입 코드, 연락처처럼 민감할 수 있는 값이 보이면 자동 저장하지 않는 guard는 P0에 포함한다.

## 입력

초기 입력은 synthetic text fixture로 시작한다.

현재 서버 entry point는 `src/server/ai/extractTripFacts.ts`의 `ExtractTripFactsInput`이고, 공유 자료 메타 타입은 `src/shared/tripFacts.ts`의 `TravelArtifact`다. 지금 타입은 자료 메타 중심이므로, P0에서 실제 문장 기반 baseline을 만들 때 text를 어디에 둘지 먼저 작게 확장한다.

```ts
type VerifyAccommodationCheckinInput = {
  artifacts: TravelArtifact[];
  materialTexts: Record<string, string>;
  userQuestion?: string;
};
```

`materialTexts`는 P0 synthetic fixture의 원문 문자열을 `artifact.id`로 연결하는 서버 입력이다. 이 이름은 구현 중 바꿀 수 있지만, 별도 `src/product` 계약을 만들지 않고 현재 `src/server/ai` entry point와 `src/shared` 타입을 기준으로 맞춘다.

P0에서는 실제 예약 PDF, 실제 screenshot, 실제 이메일을 repo에 넣지 않는다.

## 출력 계약

UI와 eval이 같은 product result를 읽을 수 있어야 한다. 새 `VerificationResult` 타입을 따로 만들지 않고, 현재 `src/shared/tripFacts.ts`의 이름을 유지하면서 P0에 필요한 필드만 확장한다.

```ts
type EvidenceState = "supported" | "needs_review" | "missing" | "conflict";

type TravelArtifact = {
  id: string;
  name: string;
  fileName: string;
  kind: "image" | "pdf" | "message" | "receipt" | "unknown";
};

type EvidenceRef = {
  artifactId: string;
  label: string;
  locator: string;
  snippet: string;
};

type TripFact = {
  id: string;
  schedule: string;
  label: string;
  value: string | null;
  confidence: number;
  evidenceState: EvidenceState;
  evidence: EvidenceRef[];
  reason?: string;
  sensitive?: boolean;
  conflictGroupId?: string;
  conflictCandidates?: {
    value: string;
    evidence: EvidenceRef[];
  }[];
};

type TripProofResult = {
  artifacts: TravelArtifact[];
  facts: TripFact[];
  openIssues: {
    id: string;
    label: string;
    reason: string;
    evidenceState: EvidenceState;
  }[];
};
```

현재 코드의 `TripFact.value`는 `string`이지만, P0의 `missing`과 `conflict`를 fact 후보로 표현하려면 `string | null` 확장이 필요할 수 있다. 구현 전에 이 확장을 먼저 판단하고, 바꾸면 이 spec과 PRD의 도메인 모델을 같이 맞춘다.

P0에서 `TripProofResult.facts`는 후보 fact 목록이다. AI나 extractor가 만든 후보 fact는 사용자가 저장하기 전까지 최종 상황 카드의 confirmed 정보가 되면 안 된다. 사용자 검수 상태는 현재처럼 `src/client/`의 local state에서 먼저 다루고, 서버/shared 계약으로 올릴 필요가 생기면 별도 작은 변경으로 연다.

P0 상태별 출력 규칙은 아래처럼 고정한다.

| EvidenceState | `value` | `evidence` | 추가 규칙 |
| --- | --- | --- | --- |
| `supported` | 자료에서 확인한 값 | 1개 이상 | `reason`은 선택이다. |
| `missing` | `null` | 빈 배열 | `reason` 또는 `openIssues` 설명은 필수다. |
| `conflict` | `null` | 빈 배열 또는 대표 근거 | `conflictCandidates`에 충돌한 값과 근거를 모두 담는다. |
| `needs_review` | 자료 값 또는 `null` | 1개 이상 가능 | 민감 값은 raw value로 넣지 않고 `sensitive: true`를 둔다. |

P0에서 evidence `snippet`은 사용자가 원문에서 다시 찾을 수 있는 문장 단위여야 한다. 단, 예약번호, 출입 코드, 전화번호처럼 민감할 수 있는 값은 snippet 안에서도 `[masked]`로 치환한다.

## Product flow

```text
자료 묶음 입력
-> 체크인 시작 시간과 늦은 도착 조건 후보 추출
-> 원문 근거 연결
-> 근거 부족, 확인 필요, 충돌 상태 부여
-> 사용자 저장/수정/무시
-> 저장된 fact만 숙소 체크인 카드에 표시
```

이 흐름이 먼저다. fixture, test, eval은 이 흐름을 만들거나 관찰하기 위해 붙는 보조층이다.

## Product entry points

P0 구현은 현재 파일 배치 안에서 아래 역할을 분리한다.

```ts
extractTripFacts(input: ExtractTripFactsInput): Promise<TripProofResult>
```

- 자료와 질문을 받아 fact 후보를 반환하는 서버 entry point다.
- P0 입력 text가 필요하면 `ExtractTripFactsInput`을 `VerifyAccommodationCheckinInput` 형태로 확장한다.
- P0에서는 accommodation check-in fixture를 통과할 만큼 deterministic baseline을 둔다.
- eval이나 fixture 파일을 import하지 않는다.

```ts
normalizeTripFacts(input: NormalizeTripFactsInput): TripProofResult
```

- raw 후보를 `supported`, `needs_review`, `missing`, `conflict` 상태로 정리한다.
- 민감하거나 근거가 약한 후보는 자동 confirmed 정보가 아니라 `openIssues`로 남긴다.
- conflict를 단일 값으로 조용히 고르지 않는다.

```ts
src/client/app.js review state and situation cards
```

- 사용자가 저장, 수정, 무시한 상태를 화면에서 반영한다.
- 저장된 fact만 confirmed 정보로 보여준다.
- 근거 부족, 충돌, 직접 확인 항목은 confirmed 정보와 분리해서 보여준다.
- 이 로직이 커지면 `src/shared` helper나 client module로 분리하되, `src/product` wrapper를 새로 만들지는 않는다.

## Acceptance criteria

- 체크인 시간이 자료에 있으면 값을 추출하고 source snippet을 함께 반환한다.
- 늦은 도착 조건이 자료에 있으면 행동 가능한 문장으로 요약하고 근거를 붙인다.
- 질문에 필요한 근거가 없으면 일반 지식으로 답하지 않는다.
- 예약번호, 출입 코드처럼 민감한 값은 자동 저장하지 않는다.
- 사용자가 저장하지 않은 후보 fact는 숙소 체크인 카드에 표시하지 않는다.
- 같은 field에 서로 다른 값이 있으면 하나로 고르지 않고 `conflict` 상태를 표현할 수 있어야 한다.
- product는 eval fixture, run artifact, metric output을 알지 않는다.

## P0 fixture cases

P0에는 아래 다섯 case를 넣는다. 이 다섯 case가 첫 기능의 완료 기준이다.

| Case | 의도 | P0 포함 판단 |
| --- | --- | --- |
| P0-A happy path | 체크인 시작 시간과 늦은 도착 조건이 모두 명확함 | 포함 |
| P0-B missing late arrival | 체크인 시간은 있지만 늦은 도착 조건이 없음 | 포함 |
| P0-C multi-doc supplement | 예약 확인서와 호스트 메시지가 서로 보완 | 포함 |
| P0-D conflict check-in time | 예약 확인서와 호스트 메시지가 서로 다른 체크인 시작 시간을 말함 | 포함 |
| P0-E sensitive guard | 출입 코드나 예약번호가 보이더라도 자동 저장하지 않음 | 포함 |

후순위 case는 아래로 둔다.

| Case | 이유 |
| --- | --- |
| cancellation ambiguity | 숙소 체크인 순간의 핵심 질문이 아니다. |
| language mix | 첫 기능 contract가 안정된 뒤 일반화한다. |
| timezone normalization | 시간대 정규화는 실제 자료 범위가 정해진 뒤 다룬다. |

## AI behavior

AI나 extractor가 붙더라도 product behavior는 아래 원칙을 지킨다.

- 자료 밖 일반 지식으로 보충하지 않는다.
- 답보다 evidence sufficiency를 먼저 본다.
- LLM output은 product contract로 정규화하고 검증한다.
- 민감하거나 애매한 값은 자동 확정하지 않는다.
- conflict를 조용히 해결하지 않는다.

## Eval 관찰 기준

eval은 product를 호출해 관찰한다. product가 eval을 import하거나 eval 전용 분기를 갖지 않는다.

| 축 | 이 slice에서 볼 질문 |
| --- | --- |
| Faithfulness/Groundedness | fact 값이 자료 내용과 맞는가 |
| Citation Precision | evidence snippet이 실제 근거인가 |
| Abstention F1 | 근거 없는 질문에서 멈추는가 |
| Conflict Recall | 서로 다른 값을 단일 답으로 뭉개지 않는가 |

아직 metric 계산식, threshold, run artifact schema는 정하지 않는다.

## 구현 순서

1. `src/shared/tripFacts.ts`가 P0 상태를 표현할 수 있는지 확인하고, 필요하면 `value: string | null`, conflict metadata, issue reason을 작게 확장한다.
2. `fixtures/accommodation-checkin/`에 P0-A부터 P0-E까지 synthetic text case를 둔다.
3. `src/server/ai/extractTripFacts.ts`가 synthetic text를 입력으로 받을 수 있게 하고 deterministic baseline을 만든다.
4. `src/server/ai/normalizeTripFacts.ts`에서 `supported`, `missing`, `conflict`, `needs_review`를 확인한다.
5. `src/client/app.js`의 review state가 저장, 수정 후 저장, 무시를 반영하고 confirmed 카드에는 저장된 fact만 쓰는지 맞춘다.
6. 테스트 또는 eval observer에서 product entry point를 호출해 P0 case를 관찰한다.
7. P0 흐름이 통과한 뒤에 LLM adapter, 실제 파일 ingestion, review UI 고도화를 별도 slice로 연다.

## 완료의 의미

P0 완료는 "숙소 체크인 AI가 똑똑하게 답한다"가 아니다. 아래가 모두 코드와 테스트로 확인되면 완료다.

- 자료에 있는 체크인 시작 시간이 근거와 함께 `supported` fact로 나온다.
- 자료에 없는 늦은 도착 조건은 `missing`으로 멈춘다.
- 서로 다른 체크인 시작 시간은 `conflict`로 나온다.
- 민감 값은 `needs_review`와 `sensitive: true`로 남고 confirmed 카드에 자동 반영되지 않는다.
- 사용자가 저장한 fact만 체크인 카드의 confirmed 정보가 된다.
- product code가 eval, fixture manifest, run artifact에 의존하지 않는다.

## 좋지 않은 구현 신호

- `supported`인데 evidence가 비어 있다.
- 자료에 없는 늦은 도착 조건을 일반 상식으로 채운다.
- 충돌 fixture에서 한 값을 골라서 정상 답처럼 보여준다.
- 후보 `facts`와 사용자가 저장한 화면 상태가 사실상 같은 배열이다.
- 출입 코드나 예약번호가 자동 저장된다.
- 테스트가 product behavior가 아니라 fixture 파일 구조만 확인한다.
- 사용자 화면 문구가 내부 metric이나 run 용어 중심이다.

## Out of scope

- 실제 PDF/OCR ingestion
- OCR bbox citation
- graph 기반 conflict system
- agent 또는 tool orchestration
- PII taxonomy 완성본
- eval dashboard
- multi-user, auth, deployment
- review UI 구현
- LLM adapter 구현

## 열린 질문

- 민감 정보 masking을 `[masked]` 수준보다 정교하게 할 필요가 있는가?
- 직접 확인이 필요한 항목의 사용자 문구를 얼마나 강하게 경고형으로 표현할 것인가?
- P0 이후 첫 확장은 LLM adapter, review UI, 실제 파일 ingestion 중 무엇인가?

## 다음 검증

1. `src/shared/tripFacts.ts`가 P0 state와 missing/conflict 값을 표현할 수 있는지 확인한다.
2. `fixtures/accommodation-checkin/`에 P0-A부터 P0-E까지 작성한다.
3. deterministic baseline으로 `supported`, `missing`, `conflict`, `needs_review` 상태를 반환하게 한다.
4. 그 결과를 테스트 또는 eval observer가 product entry point를 통해 관찰한다.
