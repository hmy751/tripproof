# Accommodation check-in slice

상태: 첫 product slice의 P0 기능 기준. 아직 구현 완료나 eval 결과를 뜻하지 않는다.

제품 전체의 어휘·상태·흐름은 통합 모델 기준 문서 `../product-model.md`를 기준으로 한다. 제품 요구사항과 경계는 `../prd.md`를 기준으로 한다. 이 문서는 그중 첫 slice인 숙소 체크인 확인만 다루며, 기준 문서의 chat-first 흐름과 상태 2축(근거 축 `EvidenceState` / 결정 축 카드 출처)을 이 도메인에 좁혀 적용한다.

## slice가 좁히는 것과 좁히지 않는 것

slice는 **도메인을 좁히는 것이지 인터랙션을 미루는 게 아니다.** 이 slice는 확인 대상을 "숙소 체크인 준비"로 좁히고, P0 필드를 두 개로 좁힌다. 그러나 기준 문서의 chat-first 흐름(자료함 → 전체 자료함 채팅 → 상태·인라인 근거가 붙은 답변 → 사람 확인·편집 카드 초안 → 일정×카테고리 대시보드 → 현장 카드)은 이 작은 도메인 안에서도 끝까지 통과시킨다. 채팅을 나중 기능으로 미루지 않는다. 채팅이 입구이자 주 인터랙션이다.

## 기능 결정

P0 기능은 `숙소 체크인 준비 확인`으로 고정한다.

사용자는 숙소 체크인 직전에 예약 확인서와 호스트 안내를 자료함(Library)에 넣고, 전체 자료함에 직접 물어 아래 두 가지를 확인한다.

- 체크인은 언제부터 가능한가?
- 늦게 도착하면 무엇을 해야 하는가?

TripProof는 이 질문에 대해 근거 없는 자유 대화 답변을 만들지 않는다. 자료에서 확인 가능한 답변(ChatAnswer)을 만들고, 답변마다 원문 근거(Evidence)와 근거 축 상태(`EvidenceState`)를 붙인다. 사용자가 카드 초안에서 확인해 올린 카드만 대시보드의 confirmed 정보가 되고, 현장 저장한 카드만 현장 카드에 표시한다.

이 기능의 본질은 "숙소 체크인 정보를 요약한다"가 아니라 "행동 전에 믿어도 되는 정보와 아직 직접 확인해야 하는 정보를 근거와 함께 분리한다"는 것이다.

## 목표

여행자가 숙소 체크인 전 받은 자료를 자료함에 넣고, 전체 자료함에 채팅으로 물어 체크인 시간과 늦은 도착 조건을 원문 근거와 함께 확인한다.

TripProof는 자료에 없는 내용을 일반 지식으로 보충하지 않는다. 자료로 답을 못 찾으면 `근거 부족`으로 멈추되, 사용자가 원문을 직접 확인해 카드로 올리는 길은 막지 않는다. 민감하거나 애매한 값은 자동 저장하지 않고 사용자가 원문 확인 후 직접 입력하게 남긴다.

## 왜 이 slice인가

숙소 체크인은 여행자가 압박 있는 순간에 확인해야 하는 정보가 작고 분명하다.

- 체크인 시간
- 늦은 도착 조건
- 예약번호 필요 여부
- 출입 방법 또는 self check-in 조건

이 slice는 TripProof의 핵심 동작을 사용자 장면 안에서 작게 포함한다.

- 자료함의 자료에 대해 채팅으로 묻고, 답변에 근거를 붙인다.
- 근거가 부족하면 멈추되, 사람이 직접 채워 올릴 수 있게 한다.
- 사용자가 카드 초안에서 확인·편집해 올린다.
- 올린 카드만 일정×카테고리 대시보드에 표시하고, 현장 저장한 카드만 현장 카드에 모은다.

## 사용자 시나리오

사용자는 숙소 근처에 있거나 이동 중이다. 예약 확인서와 호스트 체크인 안내를 자료함에 넣어 두었고, 지금 확인해야 할 것은 다음이다.

> 체크인은 몇 시부터 가능하고, 늦게 도착하면 무엇을 해야 하지?

chat-first 흐름으로 풀면 이렇게 진행된다.

1. **자료함**: 예약 확인서(PDF)와 호스트 안내(메시지)를 자료함에 넣으면 원본이 보존된다. 별도의 "여행 순간 선택" 입구는 없다.
2. **AI 추천 후보 + 전체 자료함 채팅**: 자료를 넣으면 오른쪽 rail에 "체크인 시작 시간", "늦은 도착 조건" 같은 확인 후보(AICandidate)가 뜬다. 사용자는 확인(채팅) 탭에서 전체 자료함을 대상으로 "체크인 몇 시부터?", "늦게 도착하면?"을 직접 묻는다. 문서 하나를 고르는 PDF 챗봇이 아니다.
3. **답변(상태 + 인라인 근거)**: "체크인 몇 시부터?"에 대해 자료에 근거가 있으면 `근거 있음`으로 답하고, 답변 안에서 "근거 1개 펼치기"로 원문을 인라인 확인한다. "늦게 도착하면?"이 자료에 없으면 `근거 부족`으로 멈추고 "AI가 못 찾았을 수 있으니 직접 확인이 필요하다"를 명시한다. 답변은 자동으로 카드가 되지 않는다.
4. **카드 초안(사람 확인·편집)**: 사용자가 답변이나 후보를 고르면 채팅 아래에 카드 초안(CardDraft)이 뜬다. 카테고리(숙소)·일정·이름·값을 편집한다. `근거 부족`·`자료 충돌`·민감이어도 막지 않고, 사용자가 호스트 안내 원문을 직접 확인해 늦은 도착 조건을 채워 올릴 수 있다. 이렇게 사람이 값을 채운 카드의 출처는 `직접 확인`이 된다.
5. **대시보드(일정 → 카테고리)**: 올린 카드만 대시보드 카드(DashboardCard)로 올라가, 일정(타임라인)으로 묶고 그 안을 카테고리로 나눈다. `근거 있음` 카드와 `직접 확인` 카드를 구분해 보여준다.
6. **현장 카드**: 대시보드에서 "현장 저장"을 누른 카드만 현장 카드(FieldCard)로 모여, 체크인 직전 현장에서 빠르게 다시 본다.

## P0 범위

### 포함

P0에서 끝까지 구현할 field는 아래 두 개다.

| Field id | 사용자 문구 | 기대 값 | P0 상태 |
| --- | --- | --- | --- |
| `check_in_start_time` | 체크인 시작 시간 | `3:00 PM`, `15:00`, `오후 3시 이후` 같은 자료 기반 값 | 필수 |
| `late_arrival_instruction` | 늦은 도착 조건 | `22:00 이후 도착 시 사전에 숙소에 연락` 같은 행동 가능한 조건 | 필수 |

#### 근거 축 — EvidenceState (답변 레벨)

P0에서 반드시 표현할 evidence state는 현재 `src/shared/tripFacts.ts`의 `EvidenceState`를 기준으로 한다. 이 축은 "AI가 자료로 이 답을 댈 수 있었는가"를 말하며, 답변과 후보에 붙는다.

| EvidenceState | 사용자 문구 | 의미 | P0에서 필요한 이유 |
| --- | --- | --- | --- |
| `supported` | 근거 있음 | 자료 근거로 답할 수 있음 (근거 1개 이상) | 정상 확인 결과를 표현한다. |
| `needs_review` | 확인 필요 | 근거가 있어도 민감하거나 애매해 원문 확인이 필요함 | 출입 코드처럼 자동 확정하면 위험한 값을 그대로 확정하지 않는다. |
| `missing` | 근거 부족 | 현재 자료로는 AI가 답을 못 찾음 (못 찾았을 뿐일 수 있음) | 자료에 없는 내용을 만들어내지 않는다. |
| `conflict` | 자료 충돌 | 서로 다른 자료가 같은 항목에 다른 값을 말함 | 서로 다른 체크인 시간을 하나로 합치지 않는다. |

#### 결정 축 — 카드 출처 (카드 레벨)

근거 축은 답변 레벨의 상태이고, 카드를 올릴 수 있는지를 막지 않는다. 사람이 카드로 올릴 때의 결정/출처는 별도 축이다. 이 축은 "사람이 이 정보를 카드로 어떻게 올렸는가"를 말하며, 대시보드 카드에 붙는다.

| 카드 출처 | 사용자 문구 | 의미 |
| --- | --- | --- |
| supported origin | 근거 있음 | AI의 `근거 있음` 답변을 값·이름 수정 없이 그대로 올린 카드 |
| user (직접 확인) | 직접 확인 | 사람이 원문에서 확인한 값을 채워 올린 카드. 근거가 부족/충돌이었거나, `근거 있음`이었어도 사람이 값을 고치면 이 출처로 강등된다. |
| ignored | (올리지 않음) | 답변·후보를 카드로 올리지 않기로 한 결정. 대시보드에 없다. |
| saved (현장 저장) | 현장 저장 | 대시보드 카드를 현장에서 다시 보기로 저장한 결정(overlay) → 현장 카드 |

**어휘 분리(중요):** `확인 필요`는 근거 축의 `needs_review`(답변 레벨)이고, `직접 확인`은 결정 축의 `user`(카드 레벨)다. 한 단어로 섞지 않는다. 그래서 `근거 부족` 답변도 사람이 원문에서 값을 채우면 `직접 확인` 카드로 올라가는 흐름이 모순 없이 성립한다. P0에서 별도 `manual_check` status는 만들지 않는다. 근거 축은 `needs_review`와 `sensitive: true`, `openIssues` 문구로 답변 레벨의 직접 확인 필요를 표현하고, 카드 레벨의 `직접 확인`은 `src/client/`의 카드 출처로 다룬다.

#### preview 상태 → 기준 문서 2축 매핑

`docs/archive/preview/prd.md`의 Information States 표는 근거 상태와 사람이 결정한 카드 출처를 한 표에 섞었다. 기준 문서는 이를 두 축으로 분리하며, 이 slice도 같은 매핑을 쓴다.

| preview 상태 | 사용자 문구 | 기준 문서 축 | 기준 문서 매핑 |
| --- | --- | --- | --- |
| supported | 근거 있음 | 근거 축 / (그대로 올리면) 결정 축 | `EvidenceState.supported` / supported origin |
| needs_review | 확인 필요 | 근거 축 (답변 레벨) | `EvidenceState.needs_review` |
| missing | 근거 부족 | 근거 축 (답변 레벨) | `EvidenceState.missing` |
| conflict | 자료 충돌 | 근거 축 (답변 레벨) | `EvidenceState.conflict` |
| user | 직접 확인 | 결정 축 (카드 레벨) | 카드 출처 `user` |
| saved | 현장 저장 | 결정 축 (카드 레벨) | 카드 출처 `saved` → 현장 카드 |

`supported`의 사용자 문구 `근거 있음`은 근거 축과 결정 축에 같은 단어로 나타난다 — 근거 그대로 올린 카드는 같은 라벨을 유지하기 때문이다(분리 대상은 `확인 필요`⟂`직접 확인`이다). supported 답변을 사람이 값·이름을 고쳐 올리면 `직접 확인`으로 강등된다.

### 제외

P0에서는 아래를 구현하지 않는다.

- 실제 PDF, 이미지, 이메일 ingestion
- OCR 영역 표시
- 자료함 채팅의 일반 open-ended Q&A 일반화 (P0은 체크인 두 필드 중심의 채팅만 통과시킨다)
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

`materialTexts`는 P0 synthetic fixture의 원문 문자열을 `artifact.id`로 연결하는 서버 입력이다. `artifacts`는 자료함에 들어온 자료들을 나타내고, `userQuestion`은 전체 자료함에 묻는 채팅 질문("체크인 몇 시부터?")을 받는다. 이 이름은 구현 중 바꿀 수 있지만, 별도 `src/product` 계약을 만들지 않고 현재 `src/server/ai` entry point와 `src/shared` 타입을 기준으로 맞춘다.

P0에서는 실제 예약 PDF, 실제 screenshot, 실제 이메일을 repo에 넣지 않는다.

## 출력 계약

UI(채팅 답변·카드 초안·대시보드·현장 카드)와 eval이 같은 product result를 읽을 수 있어야 한다. 새 `VerificationResult` 타입을 따로 만들지 않고, 현재 `src/shared/tripFacts.ts`의 이름을 유지하면서 P0에 필요한 필드만 확장한다.

> **주의 — 아래는 현재 코드가 아니라 P0가 도달하려는 목표 contract다.** 현재 `src/shared/tripFacts.ts`와 다른 부분(`value: string | null`, `reason?`, `conflictGroupId?`, `conflictCandidates?`)은 구현 전 확장 후보이며, 주석으로 표시했다. 확장 여부는 구현 slice에서 판단하고, 바꾸면 이 spec과 기준 문서(`../product-model.md`) 매핑을 같이 맞춘다.

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
  value: string | null;        // 현재 코드는 string. null은 확장 후보(missing/conflict 표현용)
  confidence: number;          // 코드에 존재. 단, 사용자 언어로 노출하지 않음(아래 AI behavior)
  evidenceState: EvidenceState;
  evidence: EvidenceRef[];
  reason?: string;             // 확장 후보, 현재 코드에 없음
  sensitive?: boolean;
  conflictGroupId?: string;    // 확장 후보, 현재 코드에 없음
  conflictCandidates?: {       // 확장 후보, 현재 코드에 없음
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

`TripFact`는 채팅 답변의 근거 축 상태(`evidenceState`)와 원문 근거(`evidence`)를 함께 담는다. 답변 본문 텍스트와 카드 출처(결정 축)는 이 공유 타입 밖이며, 카드 출처는 현재 `src/client/`의 local state로 둔다.

`TripFact.value`는 현재 `string`이지만, P0의 `missing`과 `conflict`를 답변 후보로 표현하려면 `string | null` 확장이 필요할 수 있다. 구현 전에 이 확장을 먼저 판단하고, 바꾸면 이 spec과 기준 문서의 도메인 매핑을 같이 맞춘다. `TripFact.confidence: number`는 코드에 존재하나, P0에서 confidence 수치를 사용자 노출이나 저장 판단 근거로 쓰지 않는다(필드 존치/제거는 코드 드리프트 follow-up). 그 외 코드 드리프트로 남겨둔 항목(`category` 필드, 카드 출처/`ReviewDecision`의 공유 타입 승격, `reason`/`conflict*` 필드)은 이 slice에서 닫지 않고 기준 문서의 확장 후보로 둔다.

P0에서 `TripProofResult.facts`는 답변/후보 fact 목록이다. AI나 extractor가 만든 후보 fact는 사용자가 카드 초안에서 확인해 올리기 전까지 대시보드의 confirmed 정보가 되면 안 된다. 카드 출처(직접 확인/근거 있음/현장 저장)는 현재처럼 `src/client/`의 local state에서 먼저 다루고, 서버/shared 계약으로 올릴 필요가 생기면 별도 작은 변경으로 연다.

P0 상태별 출력 규칙은 아래처럼 고정한다.

| EvidenceState | `value` | `evidence` | 추가 규칙 |
| --- | --- | --- | --- |
| `supported` | 자료에서 확인한 값 | 1개 이상 | `reason`은 선택이다. |
| `missing` | `null` | 빈 배열 | `reason` 또는 `openIssues` 설명은 필수다. 답변은 "AI가 못 찾았을 수 있으니 직접 확인이 필요하다"를 말한다. |
| `conflict` | `null` | 빈 배열 또는 대표 근거 | `conflictCandidates`에 충돌한 값과 근거를 모두 담는다. 양쪽 근거를 함께 보여준다. |
| `needs_review` | 자료 값 또는 `null` | 1개 이상 가능 | 민감 값은 raw value로 넣지 않고 `sensitive: true`를 둔다. |

P0에서 evidence `snippet`은 사용자가 답변 안 인라인 근거로 펼쳤을 때 원문에서 다시 찾을 수 있는 문장 단위여야 한다. 단, 예약번호, 출입 코드, 전화번호처럼 민감할 수 있는 값은 snippet 안에서도 `[masked]`로 치환한다.

## Product flow

```text
자료함 입력 (예약 확인서 + 호스트 안내)
-> AI 추천 후보 + 전체 자료함 채팅 ("체크인 몇 시부터?", "늦게 도착하면?")
-> 답변(ChatAnswer): 근거 축 상태(근거 있음/확인 필요/근거 부족/자료 충돌) + 인라인 근거
-> 카드 초안(CardDraft): 사람 확인·편집 (근거 부족·충돌이어도 직접 채워 올리기 허용 → 직접 확인 출처)
-> 대시보드(일정 → 카테고리): 올린 카드만, 근거 있음/직접 확인 구분
-> 현장 카드: 현장 저장한 카드만
```

이 흐름이 먼저다. fixture, test, eval은 이 흐름을 만들거나 관찰하기 위해 붙는 보조층이다.

## Product entry points

P0 구현은 현재 파일 배치 안에서 아래 역할을 분리한다.

```ts
extractTripFacts(input: ExtractTripFactsInput): Promise<TripProofResult>
```

- 자료함의 자료와 채팅 질문을 받아 답변/후보 fact를 반환하는 서버 entry point다.
- P0 입력 text가 필요하면 `ExtractTripFactsInput`을 `VerifyAccommodationCheckinInput` 형태로 확장한다.
- P0에서는 accommodation check-in fixture를 통과할 만큼 deterministic baseline을 둔다.
- eval이나 fixture 파일을 import하지 않는다.

```ts
normalizeTripFacts(input: NormalizeTripFactsInput): TripProofResult
```

- raw 후보를 `supported`, `needs_review`, `missing`, `conflict` 근거 축 상태로 정리한다.
- 민감하거나 근거가 약한 후보는 자동 confirmed 정보가 아니라 `openIssues`로 남긴다.
- conflict를 단일 값으로 조용히 고르지 않는다.

```ts
src/client/app.js 채팅 답변, 카드 초안, 대시보드, 현장 카드 상태
```

- 답변에 근거 축 상태와 인라인 근거 펼침을 보여준다.
- 카드 초안에서 사람이 확인·편집해 올린 카드 출처(근거 있음/직접 확인)를 반영한다.
- 근거 부족·충돌·민감이어도 카드 올리기를 막지 않고, 사람이 채워 올린 카드는 `직접 확인`으로 강등 표시한다.
- 올린 카드만 대시보드의 confirmed 정보로 보여주고, 현장 저장한 카드만 현장 카드에 모은다.
- 이 로직이 커지면 `src/shared` helper나 client module로 분리하되, `src/product` wrapper를 새로 만들지는 않는다.

## Acceptance criteria

- 체크인 시간이 자료에 있으면 값을 추출하고 답변에 인라인으로 펼칠 수 있는 source snippet을 함께 반환한다.
- 늦은 도착 조건이 자료에 있으면 행동 가능한 문장으로 요약하고 근거를 붙인다.
- 질문에 필요한 근거가 없으면 일반 지식으로 답하지 않고 `근거 부족`으로 멈춘다. 단, 사용자가 직접 채워 카드로 올리는 길은 막지 않는다.
- 예약번호, 출입 코드처럼 민감한 값은 자동 저장하지 않는다. 원문 확인 후 사람이 직접 입력한다.
- 사용자가 카드 초안에서 올리지 않은 후보 답변은 대시보드의 confirmed 정보로 표시하지 않는다.
- 같은 field에 서로 다른 값이 있으면 하나로 고르지 않고 `conflict` 상태를 표현하며 양쪽 근거를 함께 보여준다.
- `근거 있음` 답변을 사람이 값·이름을 고쳐 올리면 카드 출처를 `직접 확인`으로 강등해 AI 근거 카드와 섞지 않는다.
- product는 eval fixture, run artifact, metric output을 알지 않는다.

## P0 fixture cases

P0에는 아래 다섯 case를 넣는다. 이 다섯 case가 첫 기능의 완료 기준이다.

| Case | 의도 | P0 포함 판단 |
| --- | --- | --- |
| P0-A happy path | 체크인 시작 시간과 늦은 도착 조건이 모두 명확함 (`근거 있음`) | 포함 |
| P0-B missing late arrival | 체크인 시간은 있지만 늦은 도착 조건이 없음 (`근거 부족`으로 멈춤, 직접 확인으로 올리기는 허용) | 포함 |
| P0-C multi-doc supplement | 예약 확인서와 호스트 메시지가 서로 보완 (전체 자료함 채팅이 두 자료를 함께 근거로 댐) | 포함 |
| P0-D conflict check-in time | 예약 확인서와 호스트 메시지가 서로 다른 체크인 시작 시간을 말함 (`자료 충돌`) | 포함 |
| P0-E sensitive guard | 출입 코드나 예약번호가 보이더라도 자동 저장하지 않음 (`needs_review` + `sensitive`, snippet은 `[masked]`) | 포함 |

> **P0-D 관련 UX 메모:** `자료 충돌` 답변의 인라인 근거 표시(양쪽 값과 각 근거를 답변 안에서 어떻게 펼칠지)는 `docs/archive/preview/tripproof-preview-c.html`이 시연하지 않은 유일한 상태다(preview answerBank에는 supported/needs_review/missing 예시만 있다). preview를 UX 원천으로 삼지만 conflict만 원천이 없으므로, P0 구현 시 `conflictCandidates`를 인라인 evidence 위계 안에서 어떻게 렌더할지는 별도 UX 판단이 필요하다.

후순위 case는 아래로 둔다.

| Case | 이유 |
| --- | --- |
| cancellation ambiguity | 숙소 체크인 순간의 핵심 질문이 아니다. |
| language mix | 첫 기능 contract가 안정된 뒤 일반화한다. |
| timezone normalization | 시간대 정규화는 실제 자료 범위가 정해진 뒤 다룬다. |

## AI behavior

AI나 extractor가 붙더라도 product behavior는 아래 원칙을 지킨다.

### AI는 한다

- 답보다 evidence sufficiency를 먼저 본다.
- 답할 수 있으면 답변에 근거 축 상태와 인라인 근거를 붙인다.
- LLM output은 product contract로 정규화하고 검증한다.

### AI Must Not

- 자료 밖 일반 지식으로 답을 보충하지 않는다. 자료에 없으면 `근거 부족`으로 멈춘다.
- 서로 다른 자료의 값을 임의로 하나로 합치지 않는다. `자료 충돌`로 양쪽 근거를 함께 둔다.
- 민감 정보(예약번호·출입 코드·연락처·결제 정보)를 자동 저장하지 않는다.
- 사용자가 올리지 않은 후보 답변을 대시보드의 confirmed 정보처럼 표시하지 않는다.
- AI confidence 수치(`AI confidence 0.84`, `신뢰도 medium`)를 사용자 언어로 쓰지 않는다. 사용자 문구는 근거 있음 / 확인 필요 / 근거 부족 / 자료 충돌 / 직접 확인 / 현장 저장만 쓴다.

## Eval 관찰 기준

eval은 product를 호출해 관찰한다. product가 eval을 import하거나 eval 전용 분기를 갖지 않는다. eval 축 이름은 기준 문서와 같다.

| 축 | 이 slice에서 볼 질문 |
| --- | --- |
| Faithfulness/Groundedness | 답변의 fact 값이 자료 내용과 맞는가 |
| Citation Precision | 인라인 근거 snippet이 실제 근거인가 |
| Abstention F1 | 근거 없는 질문에서 `근거 부족`으로 멈추는가 |
| Conflict Recall | 서로 다른 값을 단일 답으로 뭉개지 않고 `자료 충돌`로 두는가 |

아직 metric 계산식, threshold, run artifact schema는 정하지 않는다.

## 구현 순서

1. `src/shared/tripFacts.ts`가 P0 근거 축 상태를 표현할 수 있는지 확인하고, 필요하면 `value: string | null`, conflict metadata, issue reason을 작게 확장한다.
2. `fixtures/accommodation-checkin/`에 P0-A부터 P0-E까지 synthetic text case를 둔다.
3. `src/server/ai/extractTripFacts.ts`가 자료함 text와 채팅 질문을 입력으로 받을 수 있게 하고 deterministic baseline을 만든다.
4. `src/server/ai/normalizeTripFacts.ts`에서 `supported`, `missing`, `conflict`, `needs_review`를 확인한다.
5. `src/client/app.js`가 채팅 답변(상태+인라인 근거) → 카드 초안(사람 확인·편집, 직접 확인 강등) → 대시보드(올린 카드만) → 현장 카드(현장 저장만) 흐름을 반영하는지 맞춘다.
6. 테스트 또는 eval observer에서 product entry point를 호출해 P0 case를 관찰한다.
7. P0 흐름이 통과한 뒤에 LLM adapter, 실제 파일 ingestion, 자료함 채팅의 일반 Q&A 일반화를 별도 slice로 연다.

## 완료의 의미

P0 완료는 "숙소 체크인 AI가 똑똑하게 답한다"가 아니다. 아래가 모두 코드와 테스트로 확인되면 완료다.

- 자료에 있는 체크인 시작 시간이 채팅 답변에서 인라인 근거와 함께 `근거 있음`으로 나온다.
- 자료에 없는 늦은 도착 조건은 `근거 부족`으로 멈추고, 사용자가 원문 확인 후 카드 초안에서 `직접 확인`으로 채워 올릴 수 있다.
- 서로 다른 체크인 시작 시간은 `자료 충돌`로 나오고 양쪽 근거를 함께 보여준다.
- 민감 값은 `needs_review`와 `sensitive: true`로 남고, snippet은 `[masked]`이며, 대시보드 confirmed 정보에 자동 반영되지 않는다.
- 사용자가 카드 초안에서 올린 카드만 대시보드의 confirmed 정보가 되고, 현장 저장한 카드만 현장 카드가 된다.
- product code가 eval, fixture manifest, run artifact에 의존하지 않는다.

## 좋지 않은 구현 신호

- `근거 있음`인데 evidence가 비어 있다.
- 자료에 없는 늦은 도착 조건을 일반 상식으로 채워 답한다.
- 충돌 fixture에서 한 값을 골라서 정상 답처럼 보여준다.
- 후보 답변(`facts`)과 사용자가 카드로 올린 화면 상태가 사실상 같은 배열이다.
- 출입 코드나 예약번호가 자동 저장된다.
- `확인 필요`(근거 축 답변 상태)와 `직접 확인`(결정 축 카드 출처)을 한 단어로 섞어 표시한다.
- `근거 있음` 답변을 사람이 값을 고쳐 올렸는데도 AI 근거 카드처럼 보여준다.
- 채팅을 나중 기능처럼 미루고 카드만 먼저 보여준다 (slice는 도메인을 좁히는 것이지 인터랙션을 미루는 게 아니다).
- 테스트가 product behavior가 아니라 fixture 파일 구조만 확인한다.
- 사용자 화면 문구가 내부 metric이나 run 용어, confidence 수치 중심이다.

## Out of scope

- 실제 PDF/OCR ingestion
- OCR bbox citation
- graph 기반 conflict system
- agent 또는 tool orchestration
- PII taxonomy 완성본
- eval dashboard
- 자료함 채팅의 일반 open-ended Q&A 일반화 (P0은 체크인 두 필드 중심)
- multi-user, auth, deployment
- LLM adapter 구현

## 열린 질문

- 민감 정보 masking을 `[masked]` 수준보다 정교하게 할 필요가 있는가?
- `근거 부족` 답변에서 "직접 확인이 필요하다"를 얼마나 강하게 경고형으로 표현할 것인가?
- `직접 확인` 카드 출처(결정 축)를 서버/eval이 읽어야 할 때 `ReviewDecision`을 공유 타입으로 언제 승격할 것인가? (현재 `src/client/` local state)
- `자료 충돌` 답변의 인라인 근거 렌더(양쪽 값·근거)를 어떤 UX로 펼칠 것인가? (preview에 원천 없음)
- P0 이후 첫 확장은 LLM adapter, 자료함 채팅 일반화, 실제 파일 ingestion 중 무엇인가?

## 다음 검증

1. `src/shared/tripFacts.ts`가 P0 근거 축 상태와 missing/conflict 값을 표현할 수 있는지 확인한다.
2. `fixtures/accommodation-checkin/`에 P0-A부터 P0-E까지 작성한다.
3. deterministic baseline으로 자료함 채팅 질문에 대해 `supported`, `missing`, `conflict`, `needs_review` 답변을 반환하게 한다.
4. 그 결과를 테스트 또는 eval observer가 product entry point를 통해 관찰한다.
