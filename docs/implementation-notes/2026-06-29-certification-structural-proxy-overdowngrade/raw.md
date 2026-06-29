# Raw Notes - certification 구조 프록시 과잉 강등 (eval 출처와 측정값)

이 파일은 `index.md` 관찰의 배경 재료다. run artifact가 `.gitignore` 대상이라(아래 경로 확인) 핵심 수치를 여기에 발췌·보존한다. 현재 실행 기준이나 작업 대기열이 아니다.

## 출처 (provenance)

- run 14 (04 적용, 측정 대상)
  - 경로: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/14-answer-certification-04-after-production/` (gitignore됨 — 커밋되지 않음)
  - created_at: `2026-06-29T07:28:42Z`
  - code: commit `08f141ecd99d3d5bee20cd3225e62a94cd4e9239`, branch `feat/04-answer-certification-boundary`, dirty `False`
  - runtime: `production` / retrieval `supabase` (top_k=3) / embedding `nomic-embed-text-v2-moe` / answer `gemma3:4b` / seed `20260624` / temperature `0.0`
  - material: `fixtures/private/accommodation-checkin/agoda-fukuoka-booking-confirmation-private.pdf`
  - questions: `eval/datasets/agoda-booking-confirmation/questions.json` (8문항)
- run 13 (04 직전 baseline, 비교 대상)
  - 경로: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/13-20260625T135431Z-answer-certification-after-production/`
  - created_at: `2026-06-25T13:55:43Z`
  - 같은 PDF·같은 questions·같은 seed(20260624)·production/supabase/gemma3:4b

두 run 모두 단일 run이다. answer composer 출력엔 run 간 비결정성이 있으므로(decision doc 관찰) evidence_state 자체는 흔들릴 수 있다. 다만 아래 강등 *사유*는 같은 후보 집합에서 결정적으로 나오므로, 진단(프록시 과적용)은 LLM 변동과 무관하다.

## evidence_state: run 13 → run 14

| 질문 | type | 기대 | run 13 | run 14 |
| --- | --- | --- | --- | --- |
| AGODA-P0-01 | checkin_action | supported | supported | needs_review (2) |
| AGODA-P0-02 | stay_dates | supported | supported (2) | needs_review |
| AGODA-P0-03 | missing_checkin_start_time | missing | missing | missing |
| AGODA-P0-04 | property_location | supported | missing | needs_review |
| AGODA-P0-05 | room_and_party | supported | supported | needs_review |
| AGODA-P0-06 | cancellation_policy | supported | supported | missing |
| AGODA-P0-07 | onsite_costs | supported | missing | needs_review |
| AGODA-P1-01 | special_request_boundary | needs_review | missing | missing |

- run 14에는 `supported`가 0개다.
- P1-01은 두 run 모두 LLM이 missing을 내서(아래 `candidate_missing`) certify의 조건 강등이 발동하지 않았다 — 이 run은 P1-01 강등을 실증하지 못한다.

## run 14 질문별 certification 전이 (proposed → state, reason)

```
AGODA-P0-01  needs_review  proposed=supported  reason=value_only_with_condition
AGODA-P0-01  needs_review  proposed=supported  reason=conditional_source_kind
AGODA-P0-02  needs_review  proposed=supported  reason=value_only_with_condition
AGODA-P0-03  missing       proposed=missing    reason=candidate_missing
AGODA-P0-04  needs_review  proposed=supported  reason=value_only_with_condition
AGODA-P0-05  needs_review  proposed=supported  reason=value_only_with_condition
AGODA-P0-06  missing       proposed=supported  reason=ungrounded
AGODA-P0-07  needs_review  proposed=supported  reason=conditional_source_kind
AGODA-P1-01  missing       proposed=missing    reason=candidate_missing
```

LLM은 6개 질문에서 supported를 제안했지만 코드 certification이 전부 내렸다(needs_review 5, missing 1).

## 후보 unit의 kind (인용 여부 표시) — 프록시가 과적용된 자리

각 질문의 retrieval 후보와 인용(CITED) unit. 강등이 무관한 조건에 걸린 게 보인다.

```
P0-02 (날짜, 기대 supported)
   CITED kind=label_value  struct=table_row_group   Arrival : 체크인: 2025년 3월 09일 ...
         kind=label_value  struct=key_value_row     체크인 : 체크아웃 :
         kind=policy       struct=field_group       [취소 정책]: ...        ← 날짜와 무관하지만 같은 page → value_only_with_condition

P0-04 (위치, 기대 supported)
   CITED kind=label_value  struct=field_group       Property : The Millennials 福岡 ...
         kind=policy       struct=heading_paragraph 비고 [ 중요 알림 ] ...   ← 같은 page → 강등

P0-05 (객실/인원, 기대 supported)
   CITED kind=label_value  struct=field_group       Number of Rooms : 1 ...
         kind=policy       struct=heading_paragraph 비고 [ 중요 알림 ] ...   ← 같은 page → 강등

P0-07 (현장비용/노쇼, 기대 supported)
   CITED kind=policy       struct=paragraph         ... 노쇼 (No-Show) ...   ← 인용 unit 자체가 policy → conditional_source_kind

P1-01 (특별요청, 기대 needs_review)
         kind=request_note struct=field_group       Remarks : NonSmoke,LargeBed 도시세 관련 안내 ...
         kind=policy       struct=heading_paragraph 비고 [ 중요 알림 ] ...
   (LLM이 missing을 내서 인용 없음)
```

관찰 포인트:

- P0-02/04/05는 인용 unit이 `label_value`(깨끗한 값)인데, 같은 page에 `policy` unit이 있다는 이유만으로 강등됐다.
- P0-07은 인용 unit이 `policy`라 강등됐는데, 이 질문은 정책이 답이라 정책 문단 인용이 정상이다.
- P1-01에선 특별요청 값과 caveat가 한 `request_note`/`field_group` unit으로 묶여 들어왔다. 즉 LLM이 이 unit을 supported로 인용했다면 `conditional_source_kind`로 잡혔을 것이다 — 이 run에선 LLM이 abstain해서 미실증.

## 재진입 메모

- 코드를 mechanical check(grounding + value-grounding)만으로 후퇴시키고, conditional_source_kind·value_only_with_condition(same-page) 강등은 제거한다.
- "조건이 값에 걸리나"는 LLM/relation extractor가 역할로 내고 `05`가 후보를 공급/관찰하며, 코드는 그 역할 구조를 읽는 의미 층으로 재귀속한다.
- 같은 비교를 다시 할 때는 위 출처 블록의 seed/PDF/questions로 production run을 재현한다.
