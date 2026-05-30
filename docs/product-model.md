# TripProof Product Model

상태: 통합 모델 기준 문서. 이 문서는 제품의 단일 어휘·상태·흐름 기준이며, 구현 완료나 eval 결과를 주장하지 않는다. 이후 모든 제품 문서(PRD, slice spec, README)는 이 기준 문서의 어휘/상태/흐름을 그대로 쓰고, 재서술하지 않고 참조한다.

이 기준 문서는 `docs/archive/preview/prd.md`와 `docs/archive/preview/tripproof-preview-c.html`의 chat-first 경험을 인터랙션·UX의 1차 기준으로 삼고, `docs/`의 acceptance·AI behavior·도메인 타입 이름·eval 축을 어휘 정렬해 흡수한다. 제품·UX·인터랙션이 충돌하면 preview를 채택한다. 단, AI 기능(추출·근거·근거 부족·충돌·민감정보 처리)의 요구와 엄밀함은 `docs/`를 보존한다 (아래 6. 레이어 소유권).

## 1. 한 줄 정의

TripProof는 여행 자료함(Library)에 넣은 PDF·캡처·메시지·영수증에 대해 AI와 묻고 답하면서, 사용자가 근거를 보거나 직접 확인한 답변만 카드로 올려 일정 순서의 대시보드와 현장 카드로 정리하는 여행 자료 확인 도구다.

## 2. 핵심 흐름

```text
자료함 (Library)
  → AI 추천 후보(AICandidate) + 전체 자료함 채팅(Library Chat)
  → 답변(ChatAnswer: 근거 축 상태 + 인라인 근거)
  → 카드 초안(CardDraft: 사람 확인·편집, 근거 부족해도 직접 채워 올리기 허용)
  → 대시보드(Dashboard: 일정 → 카테고리)
  → 현장 카드(FieldCard)
```

이 흐름은 chat-first다. 사용자는 '여행 순간'을 먼저 고르지 않는다. 자료를 자료함에 넣고, 전체 자료함에 직접 묻는 것이 입구다. 채팅은 보조 기능이 아니라 주 인터랙션이고, 채팅 로그 자체가 최종 산출물도 아니다. 카드는 사람 확인을 거친 뒤에만 대시보드에 오른다.

### 화면 위계 (탭)

이 흐름은 세 개의 상단 탭으로 나뉜다 (`docs/archive/preview/prd.md` §7, `docs/archive/preview/tripproof-preview-c.html` `data-tab="ask|board|field"`).

```text
상단 탭:
- 확인 (채팅)   : 전체 자료함 채팅 + 그 아래 카드 초안
- 대시보드       : 일정(타임라인) → 카테고리 카드
- 현장           : 현장 저장한 카드만

왼쪽 rail : 여행 요약, 자료함(Library)
오른쪽 rail: AI 추천 후보(AICandidate) — 채팅으로 / 카드 초안으로 / 근거 펼치기
```

채팅과 카드 초안은 같은 **확인 탭** 아래 한 화면에 있고, 대시보드와 현장은 별도 탭이다. 대시보드를 탭으로 분리한 이유는, 채팅·초안·대시보드·현장을 한 화면에 모두 펼치면 보기 어렵기 때문이다. 화면 세부는 preview를 참조하되, 탭 분리라는 골격은 기준 문서에 둔다.

## 3. 객체 모델

| 기준 문서 객체 | 역할 | 실제 공유 타입 매핑 (`src/shared/tripFacts.ts`) |
| --- | --- | --- |
| Trip | 확인하려는 하나의 여행 묶음 (오사카 4박 5일) | 공유 타입 없음 — UI/preview 개념. 확장 후보. |
| Artifact | 자료함에 넣은 원본 자료 | `TravelArtifact` (id, name, fileName, kind) |
| Library (자료함) | Artifact를 모으고 근거의 원천이 되는 장소 | `TripProofResult.artifacts` 배열로 표현 |
| Library Chat | 전체 자료함에 묻는 주 인터랙션 | 공유 타입 없음 — `src/client/` + `src/server/ai` 인터랙션 |
| ChatAnswer | 상태와 인라인 근거가 붙은 답변(=카드 후보) | `TripFact`(label, value, evidenceState, evidence) + 답변 본문(공유 타입 밖) |
| AICandidate | 자료를 넣자마자 AI가 제안하는 확인 후보 | `TripFact` 후보 (오른쪽 rail 제안). 확정 아님 |
| CardDraft | 카드가 되기 전 사람이 확인·편집하는 단계 | `src/client/` local state. 공유 타입 없음 |
| DashboardCard | 사람이 확정해 대시보드에 올린 카드 | 확정된 `TripFact` + 일정·카테고리·카드 출처 (카테고리·카드 출처는 현재 공유 타입에 없음 — 확장 후보) |
| FieldCard | 현장에서 다시 보기로 저장한 카드(overlay) | DashboardCard의 `현장 저장` 상태 파생. 공유 타입 없음 |
| Evidence | 답변·후보·카드가 가리키는 원문 근거 (인라인) | `EvidenceRef` (artifactId, label, locator, snippet) |
| 일정 (Schedule) | 카드의 시간축 분류 (출발 전·Day 1·공통) | `TripFact.schedule: string` |
| 카테고리 (Category) | 카드의 종류 분류 (숙소·투어·렌터카·결제) | 공유 타입 없음 — `category` 필드 확장 후보 |

확장 후보(현재 타입과 어긋나는 지점, 구현 전 별도 판단. 코드는 이번 통합에서 바꾸지 않음):

- `TripFact.value`는 현재 `string`이다. `missing`/`conflict` 후보를 값 없이 표현하려면 `string | null` 확장이 필요할 수 있다(slice spec도 이미 지적).
- `TripFact.category` 필드는 없다. 대시보드 2차 분류축을 계약으로 올리려면 추가 후보.
- 카드 출처(결정 축)를 서버/eval이 읽어야 하면 `ReviewDecision` 또는 카드 출처 필드를 공유 타입으로 승격하는 것이 후보. 현재는 `src/client/` local state로 둔다.
- conflict 표현을 위한 `conflictGroupId`, `conflictCandidates`, fact-level `reason`은 현재 공유 타입에 없다. P0 출력 계약에서 필요해지면 작게 확장한다.
- `TripFact.confidence: number`가 코드에 있으나 이 기준 문서는 사용자 언어로 쓰지 않는다(아래 5. 정직성 원칙).

## 4. 상태 2축

상태는 한 축이 아니라 두 직교 축이다. 근거 축은 "AI가 자료로 답할 수 있었는가"(답변 레벨), 결정 축은 "사람이 카드로 어떻게 올렸는가"(카드 레벨)를 말한다. **근거 축은 카드로 올릴 수 있는지를 막지 않는다.**

사용자-facing 문구는 6개이며, 나열 순서는 근거 축 4개 → 결정 축 2개로 고정한다: 근거 있음 / 확인 필요 / 근거 부족 / 자료 충돌 / 직접 확인 / 현장 저장.

### 4.1 근거 축 — EvidenceState (답변 레벨)

| EvidenceState | 사용자 문구 | 의미 | 붙는 곳 |
| --- | --- | --- | --- |
| `supported` | 근거 있음 | 현재 자료 근거로 답할 수 있음 (근거 1개 이상) | 답변 · 후보 |
| `needs_review` | 확인 필요 | 근거가 있어도 민감하거나 애매해 원문 확인이 필요함 | 답변 · 후보 |
| `missing` | 근거 부족 | 현재 자료로는 AI가 답을 못 찾음 (못 찾았을 뿐일 수 있음) | 답변 · 후보 |
| `conflict` | 자료 충돌 | 서로 다른 자료가 같은 항목에 다른 값을 말함 | 답변 · 후보 |

### 4.2 결정 축 — ReviewDecision / 카드 출처 (카드 레벨)

| 카드 출처 | 사용자 문구 | 의미 | 붙는 곳 |
| --- | --- | --- | --- |
| supported origin | 근거 있음 | AI의 supported 답변을 값·이름 수정 없이 그대로 올린 카드 | 대시보드 카드 |
| user (직접 확인) | 직접 확인 | 사람이 원문에서 확인한 값을 채워 올린 카드. 근거가 부족/충돌이었거나, supported였어도 사람이 값을 고치면 이 출처로 강등된다. | 대시보드 카드 |
| ignored | (올리지 않음) | 답변·후보를 카드로 올리지 않기로 한 결정 | 대시보드에 없음 |
| saved (현장 저장) | 현장 저장 | 대시보드 카드를 현장에서 다시 보기로 저장한 결정(overlay) | 카드 overlay → 현장 카드 |

`supported origin`은 별도의 새 출처 라벨을 붙이는 게 아니다. 근거 축의 `supported`가 사람의 수정 없이 카드까지 보존된 경우이며, preview HTML도 답변과 같은 `근거 있음` pill을 카드에 그대로 재사용한다. 그래서 '근거 있음'이라는 한 단어가 두 축에 동시에 나타나지만 직교성을 깨지 않는다 — 사람이 값·이름을 고치는 순간 `직접 확인`으로 강등되기 때문이다. (분리가 필요한 건 `확인 필요` ⟂ `직접 확인`이다.)

어휘 분리: `확인 필요`는 근거 축의 `needs_review`(답변 레벨)이고, `직접 확인`은 결정 축의 `user`(카드 레벨)다. 한 단어로 섞지 않는다. 그래서 `근거 부족`(missing) 답변도 사람이 값을 채우면 `직접 확인` 카드로 올라가는 흐름이 모순 없이 성립한다.

## 5. 정직성 원칙

- 근거 없는 답을 만들어내지 않는다. 자료에 없으면 `근거 부족`으로 멈추고 왜 답할 수 없는지 짧게 설명한다.
- 서로 다른 자료의 값을 하나로 뭉개지 않는다. `자료 충돌`로 양쪽 근거를 함께 보여준다.
- 민감 정보(예약번호·출입 코드·연락처·결제 정보)는 자동 저장하지 않는다. 원문 확인 후 사람이 직접 입력한다.
- 사람이 확인하지 않은 후보는 대시보드에 confirmed 정보처럼 표시하지 않는다.
- 근거 부족·충돌이어도 카드 올리기를 막지 않는다. AI가 못 찾았을 수 있으므로 사람이 직접 채워 올릴 수 있고, 그 카드는 `직접 확인`으로 정직하게 구분한다.
- 근거 있음(`supported`) 보증은 사람이 값·이름을 고치면 무효이므로, 그 카드는 `직접 확인`으로 강등해 AI 근거 카드와 섞이지 않게 한다.
- AI confidence 수치('AI confidence 0.84', '신뢰도 medium')를 사용자 언어로 쓰지 않는다. 사용자 문구는 근거 있음 / 확인 필요 / 근거 부족 / 자료 충돌 / 직접 확인 / 현장 저장만 쓴다.
- 내부 평가 용어나 구현 타입명을 사용자 설명의 중심에 두지 않는다.

## 6. 레이어 소유권

이 기준 문서의 핵심은 "preview냐 docs냐"를 전역에서 고르는 게 아니라, 레이어별로 원천을 정하는 것이다. preview는 화면·흐름을 리드하고, docs는 AI 기능·엄밀함을 지킨다.

| 레이어 | 원천(source of truth) | 정렬 방식 |
| --- | --- | --- |
| 개념·제품 가치 | 이 기준 문서(`docs/product-model.md`)에서 한 번 서술 | PRD/spec/README는 재서술하지 않고 참조 |
| 인터랙션·UX (chat-first, 인라인 근거, 일정×카테고리 대시보드, 현장 카드, 오른쪽 rail 후보, 탭 위계) | `docs/archive/preview/prd.md` + `docs/archive/preview/tripproof-preview-c.html` | preview를 승격해 기준 문서 흐름으로 흡수. moment-first 입구와 단일 상황 카드는 버림 |
| 요구·acceptance·AI behavior·도메인 타입 이름·eval 축 | `docs/prd.md`, `docs/specs/accommodation-checkin.md` | 내용 유지 + 기준 문서 어휘/상태 2축으로 정렬. AI Must Not(근거 없는 답 금지, 충돌 뭉개기 금지, 민감정보 자동저장 금지) 보존 |
| 프로세스·디렉토리 경계·결정 | `docs/specs/00-spec-driven-development.md`, `docs/decisions/`, `docs/development-notes.md` | docs 유지. product/eval 기본 방향 노트(`development-notes.md`)는 그대로 두고, 흐름 서술이 기준 문서와 겹치면 기준 문서를 참조 |
| 도메인 타입 정의 (실제 코드 계약) | `src/shared/tripFacts.ts` | 기준 문서가 객체→타입 매핑과 확장 후보를 명시. 코드는 이번 통합에서 바꾸지 않고 follow-up으로 기록만 함 |

이 기준 문서는 product가 먼저고 eval은 product를 관찰만 한다는 원칙(`docs/specs/00-spec-driven-development.md`)을 보존한다. eval 축 이름은 그대로 유지한다: Faithfulness/Groundedness, Citation Precision, Abstention F1, Conflict Recall.
