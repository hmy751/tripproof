# Agoda original PDF QA improvement

작성일: 2026-06-19

상태: active spec. Agoda 예약 확인서 원문 PDF에서 드러난 QA 실패를 측정하고, 그 결과를 실제 product 개선으로 이어가기 위한 상위 기준이다. `02` source unit boundary slice는 `09-20260624T072332Z-field-groups-cleaned-after-production`으로 완료했고, `03` measurement preflight는 `12-20260624T122630Z-measurement-preflight-repeat-seeded`로 구현/확인했다. 남은 product 작업은 `04` answer candidate certification, `05` question decomposition, `06` 후보 coverage 순서로 다룬다.

이 spec 묶음의 중심은 `측정 -> 실패 유형 이해 -> product 개선 -> 같은 원문 PDF로 재확인`이다. `run.json`과 HTML report는 이 흐름을 돕는 관찰 도구이지, 개선의 목표가 아니다.

관통 기준은 근거가 받쳐주는 만큼만 확신하고, 그 정합을 재현 가능하게 관찰하는 것이다. 특히 여행 예약 정보에서는 자신 있는 오답이 모르는 답보다 더 위험하므로, supported를 늘리는 것보다 근거 부족한 supported를 줄이는 일을 우선한다.

관련 문서:

- `docs/roadmap/agoda-booking-confirmation-eval-improvement.md`
- `docs/specs/2026-06-19-observation-eval-operating-model/index.md`
- `eval/datasets/agoda-booking-confirmation/questions.json`

기준 artifact:

- Eval run 묶음: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/`
- 시작 baseline(layout 개선 전, 2026-06-19): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/`
- layout v1 after(2026-06-19): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/`
- reconciliation 이후 baseline(2026-06-23): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/`
- source unit boundary final(2026-06-24): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/09-20260624T072332Z-field-groups-cleaned-after-production/` (`source-units.md` 포함)
- measurement preflight repeat(2026-06-24): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/12-20260624T122630Z-measurement-preflight-repeat-seeded/repeat.json`
- 시점별 역할·수치 비교는 `01`의 "측정 timeline과 현재 baseline", `02`의 "V1 구현 결과"와 "Field-group follow-up 구현/측정 결과"를 본다.

## 읽는 순서

1. `01-original-pdf-observation-baseline.md`
   원문 PDF를 product API에 넣어 현재 실패를 확인하고, 실패 유형을 source unit, retrieval, answer composer, 상태 검증 문제로 나누는 기준이다.
2. `02-source-unit-structure-improvement.md`
   baseline에서 확인한 문제를 바탕으로 먼저 적용한 product 개선 slice다. 원문 PDF를 더 좋은 source unit으로 쪼개 retrieval과 evidence 경로를 개선하는 데 집중했고, 2026-06-24 `09` run으로 닫았다.
3. `03-measurement-reproducibility-preflight.md`
   이후 before/after를 단일 run 인상으로 판단하지 않도록 seed, repeat, commit hash, runtime 기록을 정리한 측정 전제다.
4. `04-answer-candidate-certification.md`
   LLM이 만든 answer candidate를 final answer로 바로 믿지 않고, 코드가 source unit kind/metadata와 grounded evidence set을 보고 최종 상태를 다시 정하게 하는 첫 product safety vertical이다.
5. `05-question-decomposition-requirements.md`
   하나의 사용자 질문을 하위 evidence requirement로 나누고, 복합 질문 일부만 찾았을 때 전체를 supported로 만들지 않게 하는 기준이다.
6. `06-subrequest-retrieval-coverage.md`
   `05`의 requirement와 `04`의 certification이 필요한 후보를 더 잘 받도록 subrequest별 retrieval coverage와 missing 원인 관찰을 개선하는 기준이다.

## 왜 지금

현재 observation/report 흐름은 질문 실행 뒤 `run.json`, local observation JSONL, `report.html`을 함께 확인하게 해준다. 이제 필요한 것은 관찰 도구를 더 키우는 일이 아니라, 그 관찰을 통해 확인된 실패를 product 동작 개선으로 연결하는 일이다.

Agoda 개선 분석은 sample fixture run을 기준으로 삼지 않는다. sample text fixture를 임시 PDF로 만들어 product API를 호출하는 실행은 runner smoke나 report 렌더링 확인에는 쓸 수 있지만, Agoda 원문 PDF 개선의 근거가 될 수 없다.

`02`의 final run인 `09`에서는 source unit 후보가 크게 개선됐지만, 남은 실패가 모두 retrieval 부재로 설명되지는 않는다. 예를 들어 특별 요청 질문은 조건 문맥을 담은 후보가 이미 retrieval 결과에 있는데도 value-only 후보만 근거로 supported가 만들어졌다. 따라서 다음 순서는 후보를 더 많이 찾는 일보다, 먼저 LLM의 answer candidate를 final state로 그대로 믿지 않는 certification 계약을 세우는 일이다.

## 중심 흐름

```text
원문 Agoda PDF 실행
-> report/observation으로 실패 유형 분류
-> 첫 product 개선: source unit 구조화
-> 측정 재현성 preflight
-> LLM answer candidate를 코드가 다시 인증
-> 질문을 하위 evidence requirement로 분해
-> 부족한 후보 coverage 개선
-> 같은 원문 PDF 질문셋으로 before/after 확인
```

## 공유 규칙

- product code는 eval dataset, runner, run artifact를 import하거나 읽지 않는다.
- eval runner는 product API entry point를 호출한다. runner 내부에서 답을 만들거나 fixture expected value를 product result처럼 쓰지 않는다.
- Agoda 개선 분석용 run은 원문 PDF 입력만 사용한다. sample fixture run은 smoke 확인으로만 다룬다.
- `run.json`과 `report.html`은 보조 관찰 장치다. product 개선의 중심은 자료가 source unit, retrieval candidate, answer/evidence로 이어지는 흐름이다.
- 업체명이나 특정 질문 문구에 맞춘 예외처리로 답을 만들지 않는다.
- lexical rule은 후보 recall이나 구조 감지 보조로 쓸 수 있지만, 답변을 직접 만드는 하드코딩으로 쓰지 않는다.
- supported 상태는 evidence snippet과 source reference 없이는 성립하지 않는다.
- LLM이 `supported`라고 반환해도 final supported로 바로 통과시키지 않는다.
- 값만 있고 조건/caveat 문맥이 부족한 정보는 supported로 단정하지 않는다.
- 관련 값을 찾았지만 확정성이 부족한 정보는 값을 버리는 `missing`이 아니라 `needs_review`로 남길 수 있어야 한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## 상위 Acceptance Criteria

1. 원문 PDF run과 sample fixture smoke run의 목적이 문서와 report에서 섞이지 않는다.
2. 원문 PDF baseline에서 8개 질문의 실패를 source unit, retrieval, answer composer, 상태 검증 중 어디에 가까운지 읽을 수 있다.
3. 첫 product 개선은 source unit 구조화에 집중하고, 같은 원문 PDF 질문셋으로 before/after를 비교한다.
4. `02` 이후 before/after는 실행 조건, 코드 버전, 반복 실행 여부를 함께 보고 해석한다.
5. source unit 구조화 뒤에도 남는 실패는 measurement noise, answer certification, decomposition, retrieval coverage 중 어디에서 생기는지 이어서 분류할 수 있다.
6. 개선 결과는 `run.json` 필드 증가가 아니라 answer/evidence path 변화와 근거 부족한 supported 감소로 확인한다.

## Slice 순서

이 묶음의 다음 작업은 아래 순서를 기본으로 삼는다. 문서 번호가 구현 순서이며, 각 단계는 같은 원문 PDF 질문셋으로 다시 실행해 before/after evidence path를 읽은 뒤 다음 단계로 넘어간다.

| 순서 | 문서 | 핵심 질문 | 다음 단계로 넘어가는 신호 |
| --- | --- | --- | --- |
| 0 | `01-original-pdf-observation-baseline.md` | 원문 PDF baseline을 믿고 읽을 수 있는가 | production-like run에서 candidate/evidence/status를 질문별로 볼 수 있다 |
| 1 | `02-source-unit-structure-improvement.md` | 원문이 질문 가능한 source unit으로 들어오는가 | 완료: `09`에서 라벨-값, 정책, 비용, 요청 단위가 source unit/candidate로 보인다 |
| 2 | `03-measurement-reproducibility-preflight.md` | 이후 before/after를 noise와 구분할 수 있는가 | 완료: run artifact가 commit/runtime/repeat/seed 조건을 드러내고 단일 run을 과신하지 않는다 |
| 3 | `04-answer-candidate-certification.md` | LLM이 supported라고 해도 코드가 final state를 다시 정하는가 | P1-01 특별 요청이 value-only supported로 통과하지 않고, 찾은 값은 needs_review로 남을 수 있다 |
| 4 | `05-question-decomposition-requirements.md` | 복합 질문을 evidence requirement로 나누는가 | 체크인/체크아웃, 객실/인원, 취소/노쇼 질문이 하위 evidence requirement로 읽힌다 |
| 5 | `06-subrequest-retrieval-coverage.md` | requirement와 certification이 필요한 후보를 더 잘 받는가 | subrequest별 후보 경로와 missing 원인이 보이고 answer/evidence path가 바뀐다 |

prompt 수정은 `04`의 certification contract가 잡힌 뒤에 다룬다. 입력 source unit과 retrieval candidate가 넓고 흐릿한 상태에서 prompt만 고치는 것은 이 묶음의 기본 해법이 아니다.

## 이번 묶음에서 섞지 않는 범위

- Agoda 전용 parser나 질문별 하드코딩 답변을 만들지 않는다.
- source unit 구조화가 되기 전에 prompt 수정만으로 점수를 올리려 하지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 원본 PDF bytes나 raw provider payload를 `run.json` 또는 shared docs에 그대로 보존하지 않는다.
- LangSmith payload 정책을 바꾸지 않는다.

## 다음 slice 후보

source unit 구조화와 측정 preflight는 `02`~`03`에서 닫았고, 다음 product 작업은 아래 순서로 진행한다.

- `04-answer-candidate-certification.md`: LLM answer candidate를 final answer로 바로 믿지 않고, source unit kind/metadata와 grounded evidence set으로 최종 상태를 다시 정한다.
- `05-question-decomposition-requirements.md`: compound question을 하위 evidence requirement로 나눈다.
- `06-subrequest-retrieval-coverage.md`: `05`가 요구하고 `04`가 인증할 후보를 subrequest별로 더 잘 공급하고 missing 원인을 읽을 수 있게 한다.

## 남은 판단

- 원문 PDF 파일을 repo fixture로 보존할지, 사용자 제공 입력 경로만 지원할지는 별도 판단이다.
- source unit `kind`와 subrequest field name의 정확한 값 목록은 구현 시 현재 자료 모델과 retrieval needs에 맞춰 정한다.
- source cue / answer cue의 정확한 JSON field name은 runner와 질문셋 수정 시 정한다.
