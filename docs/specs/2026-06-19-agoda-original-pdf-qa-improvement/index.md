# Agoda original PDF QA improvement

작성일: 2026-06-19

상태: active spec. Agoda 예약 확인서 원문 PDF에서 드러난 QA 실패를 측정하고, 그 결과를 실제 product 개선으로 이어가기 위한 상위 기준이다. `02` source unit boundary slice는 `09-20260624T072332Z-field-groups-cleaned-after-production`으로 완료했고, 남은 실패는 `03`~`05`에서 이어서 다룬다.

이 spec 묶음의 중심은 `측정 -> 실패 유형 이해 -> product 개선 -> 같은 원문 PDF로 재확인`이다. `run.json`과 HTML report는 이 흐름을 돕는 관찰 도구이지, 개선의 목표가 아니다.

관련 문서:

- `docs/roadmap/agoda-booking-confirmation-eval-improvement.md`
- `docs/specs/2026-06-19-observation-eval-operating-model/index.md`
- `eval/datasets/agoda-booking-confirmation/questions.json`

기준 artifact:

- Eval run 묶음: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/`
- 현재 production-like baseline(현재 before 기준): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/` (2026-06-23, reconciliation(merge `4a51ebe`) 이후 같은 조건 재측정. 상세는 `docs/work-log.md` 2026-06-23 항목)
- 시작 baseline(layout 개선 전, 2026-06-19): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/`
- layout v1 after(2026-06-19): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/`
- source unit boundary final(2026-06-24): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/09-20260624T072332Z-field-groups-cleaned-after-production/` (`source-units.md` 포함)
- 시점별 역할·수치 비교는 `01`의 "측정 timeline과 현재 baseline", `02`의 "V1 구현 결과"와 "Field-group follow-up 구현/측정 결과"를 본다.

## 읽는 순서

1. `01-original-pdf-observation-baseline.md`
   원문 PDF를 product API에 넣어 현재 실패를 확인하고, 실패 유형을 source unit, retrieval, answer composer, 상태 검증 문제로 나누는 기준이다.
2. `02-source-unit-structure-improvement.md`
   baseline에서 확인한 문제를 바탕으로 먼저 적용한 product 개선 slice다. 원문 PDF를 더 좋은 source unit으로 쪼개 retrieval과 evidence 경로를 개선하는 데 집중했고, 2026-06-24 `09` run으로 닫았다.
3. `03-question-decomposition.md`
   source unit이 의미 단위로 잡힌 뒤, 하나의 사용자 질문을 체크인/체크아웃, 객실/인원, 취소/노쇼 같은 하위 정보 요청으로 나누는 기준이다.
4. `04-subrequest-retrieval.md`
   하위 요청별로 필요한 source unit 후보를 따로 찾고, 후보 coverage와 missing 원인을 읽을 수 있게 만드는 기준이다.
5. `05-state-validation-answer-assembly.md`
   값과 조건 문맥을 함께 검증하고, LLM을 넓은 문서 탐색자가 아니라 찾아온 근거를 설명하는 조립자로 제한하는 기준이다.

## 왜 지금

현재 observation/report 흐름은 질문 실행 뒤 `run.json`, local observation JSONL, `report.html`을 함께 확인하게 해준다. 이제 필요한 것은 관찰 도구를 더 키우는 일이 아니라, 그 관찰을 통해 확인된 실패를 product 동작 개선으로 연결하는 일이다.

Agoda 개선 분석은 sample fixture run을 기준으로 삼지 않는다. sample text fixture를 임시 PDF로 만들어 product API를 호출하는 실행은 runner smoke나 report 렌더링 확인에는 쓸 수 있지만, Agoda 원문 PDF 개선의 근거가 될 수 없다.

2026-06-19 production-like baseline은 `supabase` retrieval, Ollama embedding, Ollama answer composer로 실행했다. API/observation 연결은 정상으로 확인됐지만 8개 질문의 rule check는 모두 실패했다. 이후 layout v1(`02`)을 적용하고, main refactor와 통합(merge `4a51ebe`)한 뒤 같은 조건으로 다시 측정한 2026-06-23 run을 현재 before 기준으로 삼았다. `02`의 field-group cleanup 최종 확인은 2026-06-24 `09` run이다. 시점별 역할과 수치는 `01`의 "측정 timeline과 현재 baseline"과 `02`의 field-group 결과 섹션을 본다.

## 중심 흐름

```text
원문 Agoda PDF 실행
-> report/observation으로 실패 유형 분류
-> 첫 product 개선: source unit 구조화
-> 질문을 하위 정보 요청으로 분해
-> 하위 요청별 retrieval candidate 확보
-> 상태 검증과 답변 조립 경계 정리
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
- 값만 있고 조건 문맥이 부족한 정보는 supported로 단정하지 않는다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## 상위 Acceptance Criteria

1. 원문 PDF run과 sample fixture smoke run의 목적이 문서와 report에서 섞이지 않는다.
2. 원문 PDF baseline에서 8개 질문의 실패를 source unit, retrieval, answer composer, 상태 검증 중 어디에 가까운지 읽을 수 있다.
3. 첫 product 개선은 source unit 구조화에 집중하고, 같은 원문 PDF 질문셋으로 before/after를 비교한다.
4. source unit 구조화 뒤에도 남는 실패는 질문 분해, 하위 요청별 retrieval, 상태 검증/답변 조립 중 어디에서 생기는지 이어서 분류할 수 있다.
5. 개선 결과는 `run.json` 필드 증가가 아니라 retrieval candidate와 answer/evidence 경로 변화로 확인한다.

## Slice 순서

이 묶음의 product 개선은 아래 순서를 기본으로 삼는다. 각 단계는 같은 원문 PDF 질문셋으로 다시 실행해 before/after evidence path를 읽은 뒤 다음 단계로 넘어간다.

| 순서 | 문서 | 핵심 질문 | 다음 단계로 넘어가는 신호 |
| --- | --- | --- | --- |
| 0 | `01-original-pdf-observation-baseline.md` | 원문 PDF baseline을 믿고 읽을 수 있는가 | production-like run에서 candidate/evidence/status를 질문별로 볼 수 있다 |
| 1 | `02-source-unit-structure-improvement.md` | 원문이 질문 가능한 source unit으로 들어오는가 | 완료: `09`에서 라벨-값, 정책, 비용, 요청 단위가 source unit/candidate로 보인다 |
| 2 | `03-question-decomposition.md` | 사용자 질문의 하위 정보 요청을 놓치지 않는가 | 체크인/체크아웃, 객실/인원, 취소/노쇼가 항목별 요청으로 분리된다 |
| 3 | `04-subrequest-retrieval.md` | 각 하위 요청이 자기 근거 후보를 받는가 | 하나의 큰 후보가 모든 질문을 대표하지 않고 subrequest별 candidate가 달라진다 |
| 4 | `05-state-validation-answer-assembly.md` | 값과 조건 문맥이 함께 검증되는가 | 특별 요청, 취소/노쇼, 추가 비용이 근거 부족한 supported로 확정되지 않는다 |

prompt 수정은 4단계 이후에 다룬다. 입력 source unit과 retrieval candidate가 넓고 흐릿한 상태에서 prompt만 고치는 것은 이 묶음의 기본 해법이 아니다.

## 이번 묶음에서 섞지 않는 범위

- Agoda 전용 parser나 질문별 하드코딩 답변을 만들지 않는다.
- source unit 구조화가 되기 전에 prompt 수정만으로 점수를 올리려 하지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 원본 PDF bytes나 raw provider payload를 `run.json` 또는 shared docs에 그대로 보존하지 않는다.
- LangSmith payload 정책을 바꾸지 않는다.

## 다음 slice 후보

source unit 구조화는 `02`에서 닫았고, 남은 실패는 새 방향을 임의로 열기보다 아래 문서 순서대로 확인한다.

- `03-question-decomposition.md`: 체크인/체크아웃, 객실/인원, 취소/노쇼처럼 한 질문 안의 여러 요청을 분리한다.
- `04-subrequest-retrieval.md`: 각 하위 요청마다 필요한 source unit 후보를 따로 찾는다.
- `05-state-validation-answer-assembly.md`: 값과 조건 문맥을 함께 보지 못하면 supported를 막고, LLM은 찾아온 근거를 사용자에게 읽기 좋게 설명하는 역할로 둔다.

## 남은 판단

- 원문 PDF 파일을 repo fixture로 보존할지, 로컬 입력 path만 지원할지는 별도 판단이다.
- source unit `kind`의 정확한 값 목록은 구현 시 현재 자료 모델과 retrieval needs에 맞춰 정한다.
- source cue / answer cue의 정확한 JSON field name은 runner와 질문셋 수정 시 정한다.
