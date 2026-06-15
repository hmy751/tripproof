# 자료 충돌 workflow 개발 지도

상태: **roadmap reference**. 이 문서는 현재 작업 지시나 고정 구현 순서가 아니다. TripProof에서 “겹치는 여행 자료가 서로 다른 값을 말할 때”를 다음 기능 후보로 열어 두고, 실제 구현을 시작할 때 코드 현황과 제품 흐름을 빠르게 맞추기 위한 참고 자료다.

작성일: 2026-06-12

## 이 문서의 역할

이 문서는 자료 충돌 workflow를 구현할 때 반복해서 확인할 문제 인식과 구현면을 정리한다. 로드맵 참고 자료이므로, 실제 실행 순서와 완료 기준은 작업 시점의 코드 상태와 필요한 spec/test에서 다시 잡는다.

TripProof의 핵심 가치는 AI가 여행 자료를 그럴듯하게 요약하는 것이 아니라, 사용자가 행동하기 전에 믿어도 되는 정보와 직접 확인해야 하는 정보를 구분하게 돕는 것이다. 자료 충돌 workflow는 이 가치를 가장 선명하게 보여준다. 여러 자료가 같은 항목을 말할 때 AI가 하나를 임의로 고르지 않고, 근거를 보존하고, 관계를 분류하고, 사용자의 확정으로 카드 전이를 닫기 때문이다.

여기에 적힌 내용은 후보와 계획이다. 아직 구현되지 않은 내용은 완료된 사실처럼 다루지 않고, 실제 코드, fixture, 테스트, demo flow가 닫힌 뒤에만 완료 상태로 옮긴다.

## 핵심 문제 정의

“중복 자료” 자체가 문제가 아니다. 문제는 **겹치는 자료가 같은 여행 항목을 말할 때 그 관계가 서로 다를 수 있다**는 점이다.

예를 들어 사용자가 예약 확인서와 숙소 메시지를 함께 넣고 체크인 시작 시각을 묻는다.

| 자료 관계 | 예시 | 제품이 해야 할 일 |
| --- | --- | --- |
| 같은 slot + 같은 값 | 예약서: 체크인 15:00 / 메시지: 체크인 15:00 | 충돌이 아니라 근거 보강으로 다룬다 |
| 같은 slot + 다른 값 | 예약서: 체크인 15:00 / 메시지: 체크인 16:00 | `자료 충돌`로 양쪽 값을 보여준다 |
| 관련 항목 + 조건 차이 | 예약서: 체크인 15:00 / 메시지: 16:00 이후 도착 시 셀프체크인 | 단순 충돌로 뭉개지 않고 조건 차이 또는 확인 필요로 다룬다 |

이 기능의 본질은 “자료 충돌 pill을 붙이는 것”이 아니다. 같은 항목인지, 값이 다른지, 조건이 다른지 판단한 뒤, 사용자가 어떤 값을 확정했는지 제품 상태로 닫는 것이다.

## 문제 인식과 개발 방향

이 기능은 다음 문제 인식에서 출발한다.

1. 사용자 위험을 발견한다.
   - 여행 중 행동에 직접 영향을 주는 정보가 여러 자료에서 다르게 나오면 사용자는 잘못 움직일 수 있다.
   - AI가 하나를 골라 답하면 사용자는 충돌을 모르고 믿는다.
   - `자료 충돌`이라고만 말하면 제품 흐름이 멈춘다.

2. 정보를 구조로 분리한다.
   - 원문 source unit과 검색용 텍스트를 분리한다.
   - 답변 문장과 근거 후보를 분리한다.
   - slot, value, condition, evidence를 분리한다.
   - 답변의 근거 상태와 카드의 사용자 확정 상태를 분리한다.

3. AI output을 제품 상태로 바로 승격하지 않는다.
   - LLM output은 후보다.
   - 서버는 후보 근거가 원문에 있는지 검증한다.
   - 충돌 후보는 단일 answer value가 아니라 comparison state로 내려간다.
   - 사용자가 선택하거나 직접 입력한 값만 `직접 확인` 카드로 올라간다.

4. 테스트 가능한 계약을 남긴다.
   - 같은 slot 다른 값은 conflict가 된다.
   - 같은 값은 conflict가 아니다.
   - 조건 차이는 같은 slot conflict로 오판하지 않는다.
   - ungrounded conflict 후보는 화면에 충돌 근거처럼 보이지 않는다.
   - conflict에서 선택한 값은 AI 근거 카드가 아니라 직접 확인 카드가 된다.

이 문서가 지향하는 구현 설명은 “AI가 자료 충돌을 표시했다”가 아니라 “서로 다른 자료가 같은 항목에 다른 값을 제시할 때 claim 단위로 정규화하고, 충돌/조건 차이를 분류한 뒤, 사용자 선택을 `직접 확인` 카드 전이로 연결했다”에 가깝다.

## 현재 코드 현황과 빈 구현면

### 이미 있는 것

| 영역 | 현재 상태 | 의미 |
| --- | --- | --- |
| 제품 언어 | `docs/product-model.md`와 `docs/prd.md`에 `자료 충돌`이 근거 축 상태로 정의되어 있다 | 제품 철학과 사용자-facing label은 이미 준비되어 있다 |
| 서버 enum | `apps/server/extraction/models.py`의 `EvidenceState`에 `CONFLICT`가 있다 | 서버 타입은 conflict 상태를 표현할 수 있다 |
| 클라이언트 타입 | `apps/client/types.ts`의 `EvidenceState`에 `"conflict"`가 있다 | 화면 타입도 conflict를 받을 수 있다 |
| 채팅 UI | `ChatWorkspace`는 `conflict` pill label과 색상을 렌더링할 수 있다 | 단일 item 수준에서는 `자료 충돌` 표시가 가능하다 |
| 카드 초안 | `drafts.ts`는 supported가 아니면 manual draft로 만든다 | conflict 답변을 직접 확인 초안으로 보내는 기본 경로가 있다 |
| 대시보드 카드 | `CardCollectionPanel`은 `sourceKind === "manual"`이면 `직접 확인`으로 보여준다 | 충돌에서 사용자가 고른 값은 직접 확인 카드로 닫을 수 있다 |
| 질문 경로 | `/api/questions`는 ready material -> retrieval -> composer -> answer를 연결한다 | 자료함 질문 product path가 이미 있다 |
| 근거 검증 | `library_chat.py`는 supported item의 `source_unit_id`와 `evidence_snippet`을 원문 source unit으로 검증한다 | conflict 후보에도 같은 grounding 검증을 확장할 수 있다 |
| 관측 | question observation은 `evidence_state_counts`를 기록한다 | conflict count도 관찰 대상으로 확장 가능하다 |

### 비어 있는 것

| 영역 | 현재 빈틈 | 영향 |
| --- | --- | --- |
| prompt contract | `library_chat_answer` prompt는 `supported | missing | needs_review`만 요구한다 | LLM이 conflict를 만들 계약이 없다 |
| composer branch | `library_chat.py`는 `EvidenceState.CONFLICT`를 별도로 처리하지 않는다 | conflict payload가 와도 현재는 fallback으로 missing이 된다 |
| answer schema | `ChatAnswerItemResponse`는 단일 `value`와 flat `evidence[]`만 가진다 | 값 A/B와 각 근거를 비교해서 싣기 어렵다 |
| client type | `ChatAnswerItem`에 `conflictCandidates`가 없다 | UI가 후보별 값과 근거를 나란히 보여줄 수 없다 |
| chat UI | `AnswerItem`은 flat evidence만 렌더링한다 | conflict pill은 가능하지만 비교 workflow는 없다 |
| draft action | 현재 `onCreateDraft`는 answer item 전체에서 빈 manual draft를 만든다 | 후보 A/B 중 하나를 선택해 draft value로 넣는 경로가 없다 |
| condition classification | 같은 slot conflict와 조건 차이를 구분하는 schema/logic이 없다 | “15:00 시작”과 “16:00 이후 도착 조건”을 단순 충돌로 오판할 수 있다 |
| decision ledger | 사용자가 어떤 충돌 후보를 선택했는지 기록하는 서버/클라이언트 구조가 없다 | 첫 slice에서는 client draft state로 충분하지만 기능 설명에는 한계 문장이 필요하다 |

## 권장 제품 흐름

처음부터 모든 자료 유형과 모든 여행 항목을 다루지 않는다. 먼저 아래 흐름 하나를 화면까지 통과시킨다.

```text
예약 확인서 source unit
+ 숙소 메시지 source unit
-> 질문: "체크인 시작 시각은 몇 시야?"
-> retrieval context가 두 source unit을 composer에 전달
-> LLM/structured output이 같은 slot의 후보 두 개를 반환
-> 서버가 각 후보의 evidence snippet을 source unit 원문으로 grounding
-> 값이 다르면 ChatAnswerItem(evidenceState=conflict, conflictCandidates=[A, B])
-> ChatWorkspace가 두 후보와 각 근거를 비교 UI로 표시
-> 사용자가 A 또는 B를 선택하거나 직접 입력
-> CardDraft(sourceKind=manual, evidenceState=conflict, value=선택값)
-> DashboardCard는 `직접 확인`으로 표시
```

이 흐름에서 중요한 것은 conflict를 답변 실패로 보지 않는 것이다. conflict는 AI가 멈춘 상태가 아니라 사용자가 판단할 수 있도록 근거를 재배치한 중간 제품 상태다.

## 제안하는 응답 계약

첫 slice에서는 기존 `ChatAnswerItem`을 크게 뒤엎지 않고 optional field를 추가하는 방식이 좋다.

서버 응답 후보:

```python
class ConflictCandidateResponse(ApiModel):
    id: str
    value: str
    condition: str | None = None
    evidence: list[EvidenceRefResponse]

class ChatAnswerItemResponse(ApiModel):
    id: str
    label: str
    body: str
    evidence_state: EvidenceState = Field(alias="evidenceState")
    value: str | None = None
    evidence: list[EvidenceRefResponse] = Field(default_factory=list)
    conflict_candidates: list[ConflictCandidateResponse] = Field(
        default_factory=list,
        alias="conflictCandidates",
    )
```

클라이언트 타입 후보:

```ts
export type ConflictCandidate = {
  id: string;
  value: string;
  condition?: string | null;
  evidence: EvidenceRef[];
};

export type ChatAnswerItem = {
  id: string;
  label: string;
  body: string;
  evidenceState: EvidenceState;
  value?: string | null;
  evidence: EvidenceRef[];
  conflictCandidates?: ConflictCandidate[];
};
```

계약 해석:

- `supported`: `value`와 `evidence[]`가 primary다.
- `missing`: `value=null`, `evidence=[]`.
- `needs_review`: 근거가 있더라도 사용자가 원문 확인을 해야 하는 상태다. 필요하면 evidence를 붙일 수 있지만 첫 slice에서는 기존 동작을 유지해도 된다.
- `conflict`: `value=null`, `conflictCandidates.length >= 2`가 primary다.
- conflict item의 flat `evidence[]`는 비워 두거나 후보 evidence를 모은 summary로만 쓴다. UI는 `conflictCandidates[].evidence`를 우선한다.

이 구조를 택하면 기존 `supported/missing` 흐름을 유지하면서 conflict만 복수 후보 구조로 확장할 수 있다.

## Conflict payload 입력 계약

LLM 또는 test double이 반환할 JSON은 아래처럼 둔다.

```json
{
  "items": [
    {
      "id": "checkin_start_time",
      "label": "체크인 시작 시각",
      "body": "체크인 시작 시각이 자료마다 다릅니다. 두 근거를 확인해 선택해야 합니다.",
      "value": null,
      "evidence_state": "conflict",
      "conflict_candidates": [
        {
          "id": "booking_confirmation",
          "value": "15:00",
          "condition": null,
          "source_unit_id": "su_booking_1",
          "evidence_snippet": "Check-in starts at 15:00."
        },
        {
          "id": "host_message",
          "value": "16:00",
          "condition": null,
          "source_unit_id": "su_host_1",
          "evidence_snippet": "Check-in starts at 16:00."
        }
      ]
    }
  ]
}
```

서버는 이 payload를 그대로 믿지 않는다.

- `evidence_state`가 conflict여도 후보가 2개 미만이면 conflict가 아니다.
- 각 후보의 `source_unit_id`는 retrieval context 안에 있어야 한다.
- 각 후보의 `evidence_snippet`은 해당 source unit text에 grounding되어야 한다.
- 값이 없거나 evidence가 없는 후보는 제외한다.
- 남은 후보가 2개 미만이면 `missing` 또는 `needs_review`로 낮춘다.
- 값이 정규화 후 같으면 conflict로 두지 않는다. 첫 slice에서는 same-value case를 `supported` 또는 `needs_review`로 낮추는 단순 규칙으로 충분하다.

## 구현면 펼치기

### 1. 자료와 fixture

첫 검증에는 실제 개인정보가 들어간 여행 자료를 쓰지 않는다. 공개 가능한 synthetic material을 만든다.

필요한 장면:

- `booking-confirmation`: 체크인 시작 시각 15:00.
- `host-message-conflict`: 체크인 시작 시각 16:00.
- `host-message-same-value`: 체크인 시작 시각 15:00.
- `host-message-condition`: 16:00 이후 도착 시 셀프체크인 안내.

현재 upload API는 PDF만 받는다. 그래서 첫 구현 테스트는 두 층으로 나눈다.

- 서버 composer unit test는 `SourceUnit`을 직접 만들어 빠르게 검증한다.
- product demo는 필요하면 test helper로 PDF를 만들거나, 나중에 text material ingestion을 별도 후보로 연다.

fixture를 만들었다고 product flow가 끝난 것은 아니다. 자료가 source unit으로 들어가고, answer contract와 화면 전이를 통과해야 한다.

### 2. Retrieval

첫 slice에서 retrieval을 크게 바꾸지 않는다. `/api/questions`는 이미 top-k context를 composer에 넘긴다. 다만 conflict 흐름에서는 두 source unit이 모두 후보에 들어와야 하므로 아래를 확인한다.

- `RAG_TOP_K`가 최소 2 이상인지.
- lexical fallback에서 두 자료가 모두 query term을 포함하는지.
- source unit text에 `check-in`, `체크인`, `starts`, `시작` 같은 검색 단어가 충분한지.

retrieval이 한 후보만 가져오면 conflict classifier는 볼 재료가 없다. 하지만 첫 slice에서 검색 품질 개선 전체까지 열면 너무 커진다. 먼저 retrieval context에 두 후보가 들어오는 fixture와 test를 만든 뒤, 실패가 보이면 retrieval 개선을 다음 후보로 연다.

### 3. LLM / structured output

prompt는 conflict를 만들 수 있어야 한다.

추가할 규칙:

- 같은 질문 항목에 대해 여러 source unit이 서로 다른 값을 말하면 `evidence_state: conflict`를 사용한다.
- conflict일 때 단일 `value`를 채우지 않는다.
- `conflict_candidates`에 각 값, 조건, source unit id, evidence snippet을 넣는다.
- 조건이 다른 안내는 무조건 conflict로 만들지 않는다.
- 일반 여행 지식이나 등록되지 않은 자료로 값을 보충하지 않는다.

첫 테스트는 fake JSON client로 시작한다. 다만 실제 제품 흐름으로 설명하려면 prompt를 통해 같은 shape가 나오는 demo 또는 최소한 prompt contract test가 필요하다. fake client만 있으면 “서버가 conflict payload를 처리할 수 있다”이지 “제품이 자료 충돌을 판단한다”까지는 아니다.

### 4. 서버 검증 / grounding

`library_chat.py`에 conflict branch를 추가한다.

핵심 함수 후보:

- `_conflict_item_from_payload(...)`
- `_conflict_candidate_from_payload(...)`
- `_ground_conflict_candidate(...)`
- `_normalized_conflict_value(...)`
- `_has_distinct_candidate_values(...)`

처음에는 별도 classifier 모듈보다 composer 내부 helper로 시작해도 된다. 다만 condition classification이 커지면 `server/answers/conflicts.py` 또는 `server/extraction/conflicts.py`로 빼는 편이 좋다.

서버 판단:

- conflict 후보마다 기존 `evidence_ref_from_snippet`을 재사용한다.
- snippet grounding이 실패하면 후보를 버리거나 value window fallback을 시도한다.
- 후보 값이 모두 같은 값이면 conflict가 아니다.
- 모든 후보가 검증되지 않으면 missing으로 낮춘다.

이 단계가 중요한 이유는 LLM이 conflict라고 말해도 제품은 원문 근거가 있는 후보만 사용자에게 보여줘야 하기 때문이다.

### 5. 응답 schema와 API

`schemas/answers.py`와 client `types.ts`를 함께 바꾼다. 기존 API route는 `ChatAnswerResponse`를 그대로 반환하므로 route 자체는 크게 바꾸지 않아도 된다.

주의할 점:

- 기존 response shape는 깨지지 않게 optional field로 확장한다.
- `conflictCandidates`는 없으면 빈 배열로 내려도 된다.
- observation의 `evidence_state_counts`는 자동으로 conflict count를 포함할 수 있다.
- LangSmith/export 관측이 raw conflict candidate 전체를 노출해야 하는지는 별도 판단이다. 첫 slice에서는 counts만으로 충분할 수 있다.

### 6. Chat UI

`ChatWorkspace`의 `AnswerItem`을 conflict-aware로 바꾼다.

권장 표시:

- 상단: label + `자료 충돌` pill.
- body: “체크인 시작 시각이 자료마다 다릅니다. 원문을 확인한 뒤 선택하세요.”
- 후보 목록:
  - 값: `15:00`
  - 조건: 있으면 표시
  - 근거 snippet
  - 액션: `이 값으로 직접 확인 카드 만들기`
- 직접 입력 액션: 기존 `직접 확인으로 남기기` 유지.

좋은 UI는 conflict를 경고로만 보여주지 않고, 사용자가 다음 행동을 할 수 있게 한다. 단, 선택 버튼 문구는 “이 값으로 확정”보다 “이 값으로 직접 확인 카드 만들기”가 안전하다. AI가 확정한 것이 아니라 사용자가 선택한 것이기 때문이다.

### 7. Draft / card 전이

현재 `createDraftFromAnswerItem`은 conflict item을 manual empty draft로 만든다. 새 기능에서는 두 경로가 필요하다.

1. conflict item 전체에서 직접 입력 draft 만들기
   - 기존 동작 유지.
   - 값은 빈칸.
   - 사용자가 직접 입력한다.

2. conflict candidate 선택으로 draft 만들기
   - `createDraftFromConflictCandidate({ item, candidate })`.
   - `sourceKind: "manual"`.
   - `evidenceState: "conflict"`.
   - `value: candidate.value`.
   - `evidence: []` 또는 선택 후보 evidence를 별도 reference로 보존할지 판단.

첫 slice에서는 대시보드에서 `직접 확인`으로 보이는 것이 핵심이다. 후보 evidence를 카드에 그대로 들고 가면 “AI 근거 카드”처럼 보일 수 있다. 카드 source 영역은 `사용자 입력`으로 두고, 필요하면 나중에 “선택 전 충돌 근거”를 ledger로 분리한다.

### 8. Decision ledger / persistence

첫 slice에서 서버 저장까지 열지 않는다.

현재 카드/대시보드는 client state MVP다. 따라서 conflict decision도 처음에는 client state로 충분하다. 다만 기능 설명에는 한계를 정확히 남겨야 한다.

첫 slice 표현:

- “사용자 선택 결과를 client draft/card state로 연결했다.”

후속 slice 표현:

- “사용자 선택 ledger를 서버 계약으로 분리해 refresh 이후에도 유지했다.”

후속으로 열 경우 ledger 후보:

```ts
type UserDecisionLedgerEntry = {
  id: string;
  answerItemId: string;
  conflictSetId: string;
  selectedCandidateId?: string;
  manualValue?: string;
  decidedAt: string;
  cardDraftId: string;
};
```

### 9. 테스트 / demo / 관측

최소 테스트:

- `test_library_chat_composer_returns_conflict_item_with_grounded_candidates`
- `test_library_chat_composer_downgrades_conflict_when_candidate_evidence_is_ungrounded`
- `test_library_chat_composer_does_not_mark_same_value_candidates_as_conflict`
- `test_create_draft_from_conflict_candidate_marks_manual`

가능하면 추가:

- condition difference case.
- `/api/questions` integration에서 `evidence_state_counts`에 `conflict: 1`이 기록되는지.
- client typecheck/build.

demo flow:

1. booking 자료와 host message 자료를 넣는다.
2. “체크인 시작 시각은 몇 시야?”라고 묻는다.
3. 채팅에 `자료 충돌` pill과 두 후보가 보인다.
4. 각 후보의 근거 snippet을 확인한다.
5. 하나를 선택해 카드 초안을 만든다.
6. 초안/대시보드에서 `직접 확인`으로 보인다.

## 추천 구현 단계

### Phase 1. Conflict answer contract

목표: 서버가 conflict payload를 검증 가능한 `ChatAnswerItem`으로 만들 수 있다.

작업 후보:

- `ConflictCandidateResponse` 추가.
- `ChatAnswerItemResponse.conflict_candidates` 추가.
- `library_chat.py`에 conflict branch 추가.
- fake JSON client 기반 unit test 추가.

이 phase가 끝나면 참인 것:

- LLM/test double이 conflict payload를 주면 서버가 grounded candidate 2개를 보존한다.
- ungrounded 후보는 사용자-facing conflict로 통과하지 못한다.

아직 참이 아닌 것:

- 실제 LLM이 충돌을 안정적으로 발견한다.
- 사용자가 화면에서 후보를 선택한다.

### Phase 2. Conflict comparison UI와 draft 전이

목표: 사용자가 conflict 후보를 보고 직접 확인 카드로 보낼 수 있다.

작업 후보:

- client `ConflictCandidate` 타입 추가.
- `ChatWorkspace`에서 conflict candidate list 렌더링.
- candidate 선택 handler 추가.
- `createDraftFromConflictCandidate` 추가.
- conflict 선택 draft는 `sourceKind: manual`로 생성.

이 phase가 끝나면 참인 것:

- conflict response가 화면에서 비교 가능한 형태로 보인다.
- 후보를 선택하면 값이 들어간 직접 확인 초안이 생긴다.
- 대시보드에 올리면 `직접 확인` 카드로 보인다.

아직 참이 아닌 것:

- 서버 저장 ledger.
- refresh 후 유지.
- 모든 condition difference 분류.

### Phase 3. Prompt contract와 product demo

목표: 실제 question path에서 두 자료가 들어오면 conflict shape가 나올 수 있다.

작업 후보:

- prompt에 `conflict`와 `conflict_candidates` 계약 추가.
- source unit 2개가 retrieval context에 들어오는 fixture 또는 API test 구성.
- conflict demo용 synthetic material 작성.
- observation에서 conflict count 확인.

이 phase가 끝나면 참인 것:

- 제품 흐름에서 자료 충돌이 단일 answer value로 뭉개지지 않는다.
- demo flow로 자료 충돌 흐름을 설명할 수 있다.

아직 참이 아닌 것:

- 다양한 도메인 일반화.
- source authority 기반 정렬.
- 고도화된 contradiction-aware retrieval.

### Phase 4. Same value / condition difference 분류

목표: 겹치는 자료를 모두 conflict로 오판하지 않는다.

작업 후보:

- value normalization helper.
- `same_value` case는 conflict로 만들지 않는 test.
- `condition_difference` case를 needs_review 또는 별도 classification으로 다루는 schema 후보 검토.
- 필요하면 `ConflictClassification` 추가.

분류 후보:

```ts
type ConflictClassification =
  | "same_slot_conflict"
  | "same_value"
  | "condition_difference"
  | "not_same_slot";
```

첫 slice에서는 이 타입을 바로 사용자-facing으로 노출하지 않아도 된다. 서버 내부 reason이나 test 이름으로만 시작할 수 있다.

### Phase 5. Decision ledger와 저장

목표: conflict resolution을 client state 이상으로 보존한다.

작업 후보:

- card draft/server persistence를 먼저 열지, conflict decision만 별도 저장할지 판단.
- `UserDecisionLedger` schema 추가.
- 선택 후보 id/manual value/created card id 기록.
- refresh 후에도 선택 결과 유지 확인.

이 phase는 사용자 선택 기록을 강화하지만 첫 구현의 필수 조건은 아니다. 너무 일찍 열면 AI 판단 workflow보다 CRUD 작업이 중심이 될 수 있다.

## 좋은 slice와 나쁜 slice

좋은 slice:

- 두 source unit이 같은 slot의 다른 값을 말한다.
- 서버는 후보별 근거를 검증한다.
- 화면은 두 후보를 비교하게 한다.
- 사용자는 선택 또는 직접 입력으로 다음 행동을 한다.
- 최종 카드는 `직접 확인`으로 닫힌다.

나쁜 slice:

- `conflict` pill만 표시하고 후보 근거를 보여주지 않는다.
- LLM이 준 답변 문장을 그대로 “자료 충돌”이라고 보여준다.
- 후보 A/B가 어느 원문에서 왔는지 추적할 수 없다.
- 사용자가 선택한 값이 `근거 있음` 카드처럼 보인다.
- test fixture의 expected output만 맞추고 실제 source unit grounding을 통과하지 않는다.
- 서버 저장 ledger부터 크게 열어 UI와 AI 판단 흐름이 밀린다.

## 냄새 신호

아래 신호가 보이면 범위를 다시 본다.

- “충돌 감지”가 hard-coded `if "15:00" and "16:00"` 같은 fixture 전용 규칙이 된다.
- conflict 후보에 evidence snippet이 없는데 화면에 보여주려 한다.
- 같은 값이 여러 자료에 있는 경우까지 conflict로 처리한다.
- 조건 차이를 값 충돌로 단정한다.
- source authority rank가 사용자 확인 없이 자동 결론을 만든다.
- `직접 확인` 카드에 AI evidence가 그대로 붙어 사용자가 AI 확정값처럼 오해할 수 있다.
- retrieval이 한 source만 가져왔는데 classifier를 고도화하려 한다.
- fake client unit test만 끝내고 제품 demo가 닫혔다고 말한다.

## 구현 후 남겨야 할 근거

완료 상태를 설명하려면 아래 근거가 필요하다.

- schema:
  - `ConflictCandidateResponse` 또는 동등 구조.
  - client `ConflictCandidate` 타입.
- server logic:
  - conflict branch.
  - 후보별 source unit grounding.
  - ungrounded 후보 downgrade.
- UI:
  - conflict candidate comparison.
  - 후보 선택 또는 직접 입력 액션.
  - manual draft/card 전이.
- tests:
  - conflict happy path.
  - ungrounded downgrade.
  - same value 또는 condition difference guard.
  - draft/card manual transition.
- demo:
  - 두 자료 업로드 또는 source unit fixture.
  - 질문.
  - conflict UI.
  - 직접 확인 카드.
- 한계 문장:
  - 첫 구현은 한 slot/check-in 중심이다.
  - persistence는 client state MVP이거나 후속 slice다.
  - source authority는 자동 결론이 아니라 표시/정렬 보조로만 둔다.

이 근거가 닫히기 전에는 완료 표현 대신 “개발 후보”, “설계 방향”, “진행 중인 feature”처럼 현재 상태가 드러나는 표현을 쓴다.

## 남은 판단 질문

- 첫 demo material은 PDF 두 개로 갈 것인가, server test의 source unit fixture로 먼저 닫을 것인가?
- `conflictCandidates`의 후보 evidence를 카드까지 들고 갈 것인가, 카드에는 manual source만 남기고 ledger로 분리할 것인가?
- 같은 값이 여러 자료에 있을 때 `supported` evidence를 여러 개 보여줄 것인가, 첫 slice에서는 대표 근거만 보여줄 것인가?
- `condition_difference`를 사용자에게 어떤 문구로 보여줄 것인가? `확인 필요`로 충분한가, 별도 comparison reason이 필요한가?
- prompt가 conflict를 직접 판단하게 할 것인가, LLM은 claim 후보만 뽑고 code classifier가 비교할 것인가?
- observation/export에 conflict candidate details를 남길 것인가, count만 남길 것인가?

## 다음에 실제 구현을 시작한다면

가장 현실적인 첫 작업은 아래 순서다.

1. `ChatAnswerItemResponse`와 client type에 `conflictCandidates`를 optional로 추가한다.
2. `library_chat.py`에서 conflict payload를 검증해 `EvidenceState.CONFLICT` item으로 반환한다.
3. `test_library_chat_answer.py`에 conflict happy path와 ungrounded downgrade를 추가한다.
4. `ChatWorkspace`에서 conflict candidates를 나란히 보여준다.
5. candidate 선택으로 manual draft를 만드는 client helper를 추가한다.
6. `npm run client:typecheck`, `npm run server:test`로 계약을 확인한다.

이 1차 구현은 “전체 자료 충돌 시스템 완성”이 아니다. 하지만 기존 제품 흐름 안에 conflict라는 비어 있던 상태를 실제 사용자 workflow로 연결하는 첫 vertical slice다.
