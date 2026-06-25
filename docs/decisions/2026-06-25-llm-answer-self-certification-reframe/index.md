# 2026-06-25 - LLM 답변 자기-인증을 검증과 분리한다 — 실패 귀속 재정의

## 폴더 구성

- `index.md`: 결론과 현재 판단.
- `raw.md`: 이 결정에 이른 디버깅 여정, 거쳐온 오진과 교정, 전환의 순간들.

`raw.md`는 현재 실행 기준이 아니다. 다음 세션은 `index.md`를 먼저 읽고, 왜 이렇게 귀속했는지 필요할 때만 `raw.md`를 본다. 원본 대화 전체는 공개 repo 밖 개인 raw 기록으로 따로 보존돼 있으며, 이 결정의 판단은 아래 발췌와 코드 근거만으로 독립적으로 읽힌다.

## 맥락

Agoda 예약 확인서 QA에서 한 질문("NonSmoke, LargeBed는 확정된 조건이야?")이 반복해서 틀렸다. 제품은 이렇게 답했다.

```json
{ "body": "NonSmoke와 LargeBed는 확정된 조건입니다.", "value": "확정", "evidence_state": "supported" }
```

원문에는 같은 자료 안에 조건 문맥이 있었다 — "모든 특별 요청은 체크인 시 숙소 측의 상황에 따라 반영 여부가 결정됩니다." 즉 답은 `needs_review`여야 했는데 `supported`로 나갔다. 그리고 이건 단발이 아니라 위험한 유형이다: **여행 예약에서 "확정"은 사용자의 행동을 바꾼다.**

처음엔 이 실패를 retrieval이나 grounding 문제로 봤다. "근거가 부족하다 → sufficiency gate를 넣자", "grounding이 너무 좁다"는 식으로 실패 지점을 검증 단계 쪽으로 미뤘다. 그 프레임으로는 검색·근거 검사만 계속 고치게 되고, 같은 confident-wrong이 남았다. 이 decision은 그 오진을 멈추고 실패를 한 단계 앞으로 다시 귀속한 기록이다.

## 근거

### 실패는 검색이 못 찾아서가 아니다 — 근거는 이미 후보에 있었다

- P1-01의 실제 observation에서 조건 문맥(`u.12`, `request_note`)은 retrieval 후보에 **이미 들어와 있었다.** 최종 답이 값만 있는 `u.47`만 근거로 쓴 것이지, 자료가 없던 게 아니다.
- 따라서 "데이터가 없었다"가 아니라 "있는 조건을 안 쓰고 값만으로 확정했다"가 정확한 증상이다. retrieval recall만 고치는 방향은 이 케이스를 설명하지 못한다.

### 1급 실패는 LLM이 만든 답변 후보 자체가 틀린 것이다

- 틀린 지점은 `body`("확정된 조건입니다")와 `value`("확정")다. 근거 snippet `"NonSmoke,LargeBed"`에는 "확정"의 의미가 없다. **생성 단계에서 이미 답이 틀렸다.**
- 그런데 뒤쪽 검증은 "이 snippet이 원문에 있나?"만 물었다. 답은 yes라서 통과했다. 정작 물었어야 할 "이 body가 이 근거로 정당화되나?"는 아무도 묻지 않았다.

### 구조 원인: 한 호출이 답변·상태 인증·근거 선택을 동시에 한다 (self-certification)

- LLM이 `body`·`value`·`evidence_state`·`source_unit_id`·`evidence_snippet`을 한 번에 낸다. 코드는 그 `evidence_state=supported`를 거의 그대로 받고, citation 존재만 최소 검사한다.
- 즉 가장 어려운 판단 — "근거가 주장을 정당화하나(entailment)" — 이 LLM의 자기선언으로 묻혔다. 검증이 생성과 같은 호출 안에 있으면 검증은 생성의 편향을 상속한다.
- 이건 카드 데이터 구조(필드형 자료)에 답변 흐름을 끼워 맞추다 앞단(검색·조립)과 뒷단(검증)의 경계가 흐려진 데서 왔다. "앞단은 단순, 뒷단이 복잡"인 구조여야 하는데, 뒷단이 citation 검사로 얇아져 있었다.

### 코드에서 확인된 자리

- `apps/server/answers/library_chat.py` `_format_source_blocks`: 프롬프트에 `source_unit_id·locator·text`만 직렬화하고 source unit의 `metadata`(조건/요청 구분)를 버린다.
- `apps/server/extraction/evidence.py` `_ground_snippet`: snippet이 원문에 substring으로 있는지만 본다. entailment는 안 본다.
- `library_chat.py` `_supported_value_matches_question`: 강등 게이트가 시간 질문에만 답 모양을 검사하고 나머지는 통과시킨다(주석이 "MISSING은 실제 grounding 실패와 구분되지 않는다"고 자인).
- `apps/server/extraction/models.py` `EvidenceState`: `CONFLICT`가 enum에는 있으나 dispatch/prompt로 라우팅되지 않는다.

## 결정

### 1. 실패 귀속을 retrieval/grounding에서 answer self-certification으로 옮긴다

이 유형의 1급 원인은 검색 부재나 grounding 버그가 아니라, LLM 답변 후보(body/value/state)를 코드가 의미 검증 없이 final answer로 받아준 것이다. 실패를 component에 귀속할 때 retrieval / 맥락 구성 / LLM 해석 / **certification(상태 게이트)** / 표시 변환을 갈라 보고, 이 케이스는 certification 층에 둔다.

### 2. 다음 설계 방향은 answer candidate validation이다 (생성과 검증 분리)

LLM 답변 후보를 final `ChatAnswerItem`으로 바로 projection하지 않고, 그 사이에 명시적 후보를 두고 코드/별도 검사가 body·value·state가 cited evidence와 질문 요구에 의해 정당화되는지 본다. 검증 기준은 "근거 존재"가 아니라 "근거가 주장을 entail함"이다. 구체 구현(코드 entailment vs 별도 judge, gate 위치)은 이 결정이 정하지 않는다 — roadmap이 소유한다.

### 3. 이 판단 감각은 일반화해 engineering lens에 둔다

이 케이스를 특정 PDF·질문에 대한 예외처리로 닫지 않고, "LLM을 제품 동작에 넣을 때 어디까지 맡기고 어디서 코드로 잡나"의 일반 기준으로 올린다. 그 자리는 [docs/engineering/llm-design.md](../../engineering/llm-design.md)다. 이 decision은 그 lens의 근거 사례이고, llm-design.md의 입력·출력·측정 예시는 위 코드 자리에 grounding돼 있다.

## 기각 또는 보류

- 특별 요청 문자열(`NonSmoke`, `LargeBed`)만 보면 needs_review로 바꾸기 — 기각(다음 자료에서 무너지는 하드코딩).
- Agoda 전용 필드 파서 — 기각([roadmap](../../roadmap/agoda-booking-confirmation-eval-improvement.md)과 같은 결).
- supported를 늘리려 grounding을 느슨하게 — 기각(방향이 반대다. 근거 부족한 supported를 줄이는 게 우선).
- prompt에 "조건을 고려하라"를 더해 막기 — 보류(prompt는 상태를 보장하지 못한다. 코드 계약이 보장한다. prompt 수정은 입력 단위·후보가 정리된 뒤다).
- validation vertical 구현 — 이 결정 밖. 방향만 정하고 구현은 roadmap 슬라이스로 둔다.

## 검증

- 확인된 사실: 위 "코드에서 확인된 자리"의 함수들은 현재 repo에 그대로 있다. P1-01의 조건 문맥이 retrieval 후보에 들어왔던 것은 해당 run의 observation에서 확인했다.
- 측정 관찰: 현재 질문셋에서 깨끗이 통과하는 건 날짜 같은 field lookup이고, 종합이 필요한 질문은 confident-wrong이거나 miss다. 취소·추가비용 질문은 같은 입력에도 run마다 `supported`↔`missing`으로 뒤집힌다(seeded 반복 실행 관찰).
- 아직 검증 안 됨: answer candidate validation은 미구현이므로 before/after 개선 수치는 없다. 이 decision은 귀속과 방향을 정한 것이지 개선을 증명한 것이 아니다.

## 이번 결정 밖

- validation vertical, question decomposition, 구조 기반 source unit의 실제 구현 — [roadmap](../../roadmap/agoda-booking-confirmation-eval-improvement.md)이 소유한다.
- entailment 검증을 코드로 할지 별도 모델로 할지 — 미정.
- conflict 상태의 dispatch/prompt 라우팅 — 미구현([material-conflict-workflow-reference](../../roadmap/material-conflict-workflow-reference.md)).
- LLM lens 문서 자체의 신설 근거 — [2026-06-22 엔지니어링 판단 기준 문서 신설](../2026-06-22-engineering-principle-docs/index.md)이 소유한다.
