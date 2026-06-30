# 2026-06-29 - certification 구조 프록시가 실제 문서에서 과잉 강등

## 폴더 구성

- `index.md`: 독립적으로 읽히는 관찰과 다음에 볼 경계.
- `raw.md`: eval run 14의 출처와 실제 측정값(13 대비 표, 질문별 강등 사유, 후보 kind). run artifact가 gitignore라 핵심 수치를 여기에 보존한다.

## 왜 남기나

`04` certification을 처음 구현할 때, "값-only 근거는 조건/caveat 없이 supported 불가"라는 계약을 코드로 강제하려고 두 개의 구조 강등 규칙을 넣었다.

- `conditional_source_kind`: 인용한 source unit의 `kind`가 조건성(policy/warning/request_note/fee)이면 강등.
- `value_only_with_condition`: 인용 unit은 값인데, 같은 page에 조건성 kind unit이 따로 있으면 강등.

단위 테스트(격리된 2~3 unit context)는 통과했지만, **실제 원문 PDF로 product flow를 돌리자 거의 모든 답이 강등됐다.** 두 규칙이 "조건이 이 값에 걸리는가"라는 의미 판단을 `kind` 딱지와 page 근접으로 흉내 낸 자리이고, 실제 문서 밀도에서 그 흉내가 무너진 것이다. 다음 구현이 같은 자리에 다시 빠지지 않도록 경계와 repro를 남긴다.

## 관찰

같은 원문 PDF·같은 `questions.json`·같은 seed로 production eval을 돌린 결과(run 14, 상세 출처/수치는 `raw.md`):

- **`04` 적용 후 supported가 0개.** `04` 직전 baseline(run 13)에서 supported였던 날짜(P0-02)·위치(P0-04)·객실(P0-05)·체크인 제시물(P0-01)이 모두 `needs_review`로 떨어졌다.
- 강등 사유는 두 신규 규칙이 지배적이었다: `value_only_with_condition`(P0-01·02·04·05), `conditional_source_kind`(P0-01·07).
- 원인 1 — **같은 page 규칙이 1~2장 문서에서 붕괴.** 예약 확인서는 한 page에 취소정책(policy)·도시세(fee)·특별요청(request_note)·중요알림(warning)이 다 모여 있다. 그래서 날짜처럼 조건과 무관한 깨끗한 값(cited `kind=label_value`)도 "같은 page에 조건 있음"으로 강등됐다. 1장 문서에서 "같은 page"는 사실상 "문서 전체"라 근접성 프록시가 의미를 잃는다.
- 원인 2 — **`conditional_source_kind`가 정당한 정책 답까지 강등.** 노쇼/현장비용(P0-07)은 답 자체가 정책 문단인데, 인용 unit이 `policy` kind라는 이유만으로 `needs_review`가 됐다. 정책 문단이 질문에 충분히 답하는지 아닌지를 가르는 건 의미 판단이라 `kind`만으로는 못 한다.
- 단위 테스트가 못 잡은 이유: 테스트는 값 1 + 조건 1처럼 격리된 context였는데, 실제 문서는 빽빽해서 "조건이 근처에/같은 종류로 존재" 신호가 거의 항상 켜진다.

핵심: **두 규칙은 "조건이 이 값에 *적용*되는가"의 거친 근사인데, "실제로 그 값을 지배하는 조건"과 "그냥 근처에/같은 종류로 존재하는 조건"을 구분하지 못한다.** 그 구분이 곧 보류해둔 entailment(근거가 주장을 받쳐주는지)다.

## 방향 (이번 관찰로 정한 것)

코드의 역할을 "할 수 있는 것"으로 후퇴시킨다.

- 코드 certification(`04`)이 정당하게 하는 일: grounding(근거가 원문에 있나), value-grounding(답한 값이 원문에 실재하나 — "확정"을 값으로 들고 오면 여기서 걸림), 그리고 LLM/추출기가 만든 역할 구성을 읽는 일.
- 코드가 하지 않을 일: `kind`·page 근접으로 "조건이 값에 걸린다"를 추정하는 것. 이 의미 판단은 LLM/relation extractor의 몫이고(`docs/engineering/llm-design.md`), 그 후보 공급/관찰은 `05` retrieval coverage가 받친다. 코드는 그 결과(역할 구조)를 받아 상태만 정한다.

따라서 `04`의 강제 범위는 candidate/certify/body 분리 + 두 mechanical check까지로 좁히고, "조건이 값에 걸리나"의 판단은 의미 층(relation/entailment, `05` 위)으로 재귀속한다.

## 검증 (run 15)

위 방향을 적용한 뒤(certify에서 `conditional_source_kind`·same-page `value_only_with_condition` 제거, grounding/value-grounding만 유지) 같은 원문 PDF·questions·seed로 production run을 다시 돌렸다(run 15, 출처/수치는 `raw.md`).

- 과잉강등 해소: run 14에서 `supported`가 0개였는데, run 15는 날짜·위치·객실·체크인 제시물·취소정책(P0-01·02·04·05·06)이 `supported`로 복구됐다.
- 제거한 두 규칙 사유는 0건. run 15의 certification 사유 집합은 `{grounded_value, candidate_missing}`뿐이었다.
- 코드가 강등을 강요하지 않음: 남은 `missing`(P0-03·07·P1-01)은 전부 `candidate_missing` — LLM이 스스로 missing을 낸 것이고 코드가 내린 게 아니다.
- 단, P1-01(특별요청 needs_review)의 안전망은 이 run에서 실증되지 않았다. LLM이 abstain(`candidate_missing`)해서 value-grounding 강등("확정"을 값으로 → needs_review)이 발동할 입력 자체가 없었다. 그 강등은 단위 테스트로만 증명되며(value="확정"), LLM이 supported+"확정"을 낼 때 안정적으로 잡으려면 의미 층이 필요하다 — 이번 코드 fix의 범위 밖이다.

즉 이 fix의 목표(과잉강등 제거, 깨끗한 값 supported 복구, 코드는 mechanical만)는 실제 데이터로 달성됐고, 조건-지배 판단은 의도대로 의미 층 몫으로 남았다.

## 다시 볼 경계

certification/상태 게이트를 구현할 때 멈춰서 확인한다.

- 코드가 "조건이 이 값에 걸리나"를 `kind`/page 근접 같은 구조 신호로 추정하고 있지 않나? 그건 의미 판단이고, 실제 문서 밀도에서 무관한 경우까지 걸린다.
- 안전 기본값(`needs_review`)을 product-first와 함께 본다. "근거 부족한 supported를 줄인다"가 "근거 있는 supported(깨끗한 값 lookup)까지 다 강등"이 되면 product가 아무것도 확정 못 해 못 쓰게 된다. 전부 needs_review는 confident-wrong의 반대쪽 실패다.
- 단위 테스트가 격리된 소수 unit context면, 실제 문서 밀도에서의 동작을 product flow eval로 따로 확인한다. 격리 테스트 통과 != product 통과.

## 어디에는 남기지 않았나

- 자기인증 실패의 귀속과 방향(LLM 후보 ↔ 코드 검증 분리)은 `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`가 소유한다. 이 노트는 그 방향을 구현한 뒤 *구조 프록시 자체가 실제 문서에서 무너진* 관찰만 본다.
- 질문/답변 단어 게이트(거울상 함정)는 `docs/implementation-notes/2026-06-29-certification-keyword-gate-mirror-trap/`. 이번 건은 단어가 아니라 *구조 프록시*가 과적용된 다른 자리다.
- 일반 원칙(의미 분류는 LLM/relation extractor, 코드는 구조 사실)은 `docs/engineering/llm-design.md`.
- `04`가 강제하는 계약 범위와 재귀속은 `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/04-answer-certification-boundary.md`.
- 조건 후보 공급/coverage 관찰 계약은 `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/05-subrequest-retrieval-coverage.md`.
