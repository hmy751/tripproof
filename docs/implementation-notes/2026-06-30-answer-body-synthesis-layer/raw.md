# raw — 답변 body 합성 A/B (run 26·27)

run artifact는 gitignore다. 아래 출처 경로와 핵심 수치를 보존한다.

## run 출처

공통: production runtime, material `fixtures/private/accommodation-checkin/agoda-fukuoka-booking-confirmation-private.pdf`, questions `eval/datasets/agoda-booking-confirmation/questions.json`, retrieval supabase top_k 3 / threshold 0.0, embedding `nomic-embed-text-v2-moe`(768), seed 20260624, temperature 0.0, repeat 3, caveat 분리 호출 disabled, 합성 모델 `gemma3:4b`.

- A (답변 `gemma3:4b`): `eval/runs/question-dataset/26-20260630T-answer-gemma4b-body-gemma4b-caveat-disabled-A/` (repeat.json은 run-group 폴더, 개별 run은 `-r01`·`-r02`·`-r03` 접미사 폴더)
- B (답변 `qwen3:14b`): `eval/runs/question-dataset/27-20260630T-answer-qwen14b-body-gemma4b-caveat-disabled-B/` (동일 구조)

두 run의 기록 `code_version`은 `5872c78`(dirty working tree)다 — 이 working tree의 08 구현이 이후 commit `84fbb18`로 들어갔다. body 합성 토글은 그 커밋에서 추가됐고 기본 on이라, 합성을 켠 채 돈 run 26/27의 측정 동작은 토글 유무와 무관하다.

## rule pass (8문항 중)

| repeat | A `gemma3:4b` | B `qwen3:14b` |
| --- | --- | --- |
| r01 | 1 | 2 |
| r02 | 1 | 2 |
| r03 | 1 | 2 |

## 문항별 처리 시간 (observation export 타임스탬프 간격, 추론)

명시 duration 필드는 기록에 없다. observation export의 `exported_at`이 완료 순서대로 찍혀 그 간격을 문항 처리 시간으로 본다(순차 spacing 확인됨). 이 시간은 답변 호출 + body 합성 호출을 합친 것이고, 양 arm 모두 합성은 `gemma3:4b`라 차이는 답변 모델에서 온다.

| repeat | A 8문항 합 / 평균 | B 8문항 합 / 평균 |
| --- | --- | --- |
| r01 | 60s / 7.4s | 387s / 48.4s |
| r02 | 48s / 6.0s | 379s / 47.4s |
| r03 | 49s / 6.1s | 388s / 48.5s |

r03 문항별 (B `qwen3:14b` ↔ A `gemma3:4b`):

| 문항 | B | A |
| --- | --- | --- |
| P0-01 준비물 | 71.8s | 6.4s |
| P0-02 날짜 | 42.3s | 8.0s |
| P0-03 체크인 시각 | 36.3s | 6.1s |
| P0-04 위치 | 34.3s | 4.7s |
| P0-05 객실/인원 | 43.0s | 6.6s |
| P0-06 취소/노쇼 | 61.3s | 6.3s |
| P0-07 추가비용 | 51.1s | 4.7s |
| P1-01 특별요청 | 48.1s | 5.9s |

## P1-01 trace (r03)

질문: "NonSmoke, LargeBed는 확정된 조건이야?" · 기대 state `needs_review`.

검색 후보(두 arm 동일): top `su_…_1_12`(p.1 u.12, score 0.367). 원문에 "Remarks : NonSmoke,LargeBed … 모든 특별 요청은 체크인 시 숙소 측의 상황에 따라 반영 여부가 결정됩니다" 포함.

A (`gemma3:4b`): certification `{proposed_state: supported, reason: ungrounded, state: missing}`, value null, evidence []. body(template) "현재 등록된 자료에서 …의 근거를 확인하지 못했습니다." rule_check `{state_matched: false, missing_cues: ["Remarks","모든 특별 요청","숙소 측의 상황"], passed: false}`.

B (`qwen3:14b`): certification `{proposed_state: supported, caveat_source: inline, caveat_snippet: "모든 특별 요청은 … 결정됩니다", reason: limited_by_caveat, state: needs_review}`, evidence `[su_…_1_12, p.1 u.12]`. body(합성) "NonSmoke 및 LargeBed 요청은 체크인 시 숙소 상황에 따라 변경될 수 있습니다." rule_check `{state_matched: true, missing_cues: ["Remarks"], passed: false}`.

대비: 같은 후보·같은 조건 문장인데 qwen은 inline caveat을 냈고 gemma는 못 냈다. certify는 그 inline caveat의 grounding만 보고 강등했다(의미 재분류 없음). B의 fail은 품질 실패가 아니라 cue 부분문자열("Remarks") 누락이다.

## 참고: 다른 문항 완성도 차이 (r03)

- P0-01 준비물: A "예약 확정서"만(1항목) / B "예약 확정서 + 유효 신분증 + 결제 신용카드"(3항목, pass).
- P0-04 위치: A `missing` / B는 숙소명·도시·국가를 답함(단 cue 단어 불일치로 fail).
- P0-06 취소/노쇼·P0-07 추가비용: B가 부분 답(노쇼 100%, 도시세 needs_review)하나 cue·인용 미달로 fail — selection/인용 벽(`05` 영역)이지 합성층 문제가 아니다.
