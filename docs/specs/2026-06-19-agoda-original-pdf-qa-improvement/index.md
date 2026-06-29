# Agoda original PDF QA improvement

작성일: 2026-06-19

상태: active spec. Agoda 예약 확인서 원문 PDF에서 드러난 QA 실패를 측정하고, 그 결과를 실제 product 개선으로 이어가기 위한 상위 기준이다. `02` source unit boundary slice는 `09-20260624T072332Z-field-groups-cleaned-after-production`으로 완료했고, `03` measurement preflight는 `12-20260624T122630Z-measurement-preflight-repeat-seeded`로 구현/확인했다. 남은 product 작업은 `04` answer certification boundary(구현됨), `05` 후보 coverage, `06` 근거 관계 추출(의미 층) 순서로 다룬다. `04`는 코드가 grounding/value-grounding 같은 mechanical check만 강제하는 범위로 좁혔고, "조건이 값을 좌우하는가"의 의미 판단은 `06` 의미 층으로 재귀속했다(근거: `04`의 `구현 범위 재조정`, `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`). `06`은 v1(분리 호출)을 시도했으나(`574dee4`) gemma3:4b가 무관한 조건을 과잉 부착해, per-unit·순서불변 변형(`118a916`)을 되돌리고(`8040665`) 더 강한 모델/접근을 기다린다(eval run 16~19 출처·수치: `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`).

이 spec 묶음의 중심은 `측정 -> 실패 유형 이해 -> product 개선 -> 같은 원문 PDF로 재확인`이다. `run.json`과 HTML report는 이 흐름을 돕는 관찰 도구이지, 개선의 목표가 아니다.

관통 기준은 근거가 받쳐주는 만큼만 확신하고, 그 정합을 재현 가능하게 관찰하는 것이다. 특히 여행 예약 정보에서는 자신 있는 오답이 모르는 답보다 더 위험하므로, supported를 늘리는 것보다 근거 부족한 supported를 줄이는 일을 우선한다.

관련 문서:

- `docs/roadmap/agoda-booking-confirmation-eval-improvement.md` (초기 개선 지도. 04 이후 현재 slice 순서는 이 spec을 우선한다.)
- `docs/specs/2026-06-19-observation-eval-operating-model/index.md`
- `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`
- `docs/implementation-notes/2026-06-29-certification-keyword-gate-mirror-trap/`
- `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`
- `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`
- `docs/engineering/llm-design.md`
- `eval/datasets/agoda-booking-confirmation/questions.json`

기준 artifact:

- Eval run 묶음: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/`
- 시작 baseline(layout 개선 전, 2026-06-19): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/`
- layout v1 after(2026-06-19): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/`
- reconciliation 이후 baseline(2026-06-23): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/`
- source unit boundary final(2026-06-24): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/09-20260624T072332Z-field-groups-cleaned-after-production/` (`source-units.md` 포함)
- measurement preflight repeat(2026-06-24): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/12-20260624T122630Z-measurement-preflight-repeat-seeded/repeat.json`
- `04` answer certification 과잉강등 관측(2026-06-29, code `08f141e`): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/14-answer-certification-04-after-production/`
- `04` answer certification mechanical-only 해소 검증(2026-06-29, 이후 `989727c` 커밋): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/15-answer-certification-mechanical-only/` (상세 출처·수치: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`)
- `06` relation pass 실험(2026-06-29, run 16~19, A/B는 되돌림): run-id 폴더별 출처·수치는 `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`(`raw.md`). 코드: inline `5d1880f`(run 16), 분리 호출 `574dee4`(run 17), per-unit·순서불변 `118a916`(run 18·19).
- 시점별 역할·수치 비교는 `01`의 "측정 timeline과 현재 baseline", `02`의 "V1 구현 결과"와 "Field-group follow-up 구현/측정 결과"를 본다.

## 읽는 순서

1. `01-original-pdf-observation-baseline.md`
   원문 PDF를 product API에 넣어 현재 실패를 확인하고, 실패 유형을 source unit, retrieval, answer composer, 상태 검증 문제로 나누는 기준이다.
2. `02-source-unit-structure-improvement.md`
   baseline에서 확인한 문제를 바탕으로 먼저 적용한 product 개선 slice다. 원문 PDF를 더 좋은 source unit으로 쪼개 retrieval과 evidence 경로를 개선하는 데 집중했고, 2026-06-24 `09` run으로 닫았다.
3. `03-measurement-reproducibility-preflight.md`
   이후 before/after를 단일 run 인상으로 판단하지 않도록 seed, repeat, commit hash, runtime 기록을 정리한 측정 전제다.
4. `04-answer-certification-boundary.md`
   LLM 답변 후보와 final answer 사이에 code-owned certification boundary를 두는 첫 product safety vertical이다. 코드가 강제하는 것은 candidate↔final 분리와 mechanical check(grounding, value-grounding — "확정"을 값으로 들고 오면 차단)까지로 좁혔고, "값을 좌우하는 조건이 있는가"의 의미 판단은 `06`으로 재귀속했다.
5. `05-subrequest-retrieval-coverage.md`
   하위 요청(role)별로 필요한 source unit 후보를 더 안정적으로 공급하고, 후보가 없을 때 원인을 구분하는 retrieval coverage 기준이다. 후보가 값만 담는지 조건 문맥도 담는지를 관찰해 `06`에 넘기지만, "그 조건이 이 값을 좌우하는가"의 판정은 하지 않는다.
6. `06-evidence-relation-extraction.md`
   이미 후보에 들어온 값과 caveat 사이의 역할·관계를 만드는 의미 층이다. "이 값은 이 조건에 좌우된다 / 필요한 조건 역할이 비었다"를 LLM/relation extractor가 역할로 내면, `04` 코드 certification이 그 역할 구조를 읽어 state를 정한다. P1-01(값을 좌우하는 조건이 있는데 "확정"으로 답한 실패)을 안정적으로 막는 자리다.
7. `07-relation-vs-model-upgrade-ab.md`
   `06`이 gemma3:4b 정밀도 천장에 막힌 뒤, 다음 수를 A/B 측정으로 정한다 — relation 층 유지+강한 모델(A) vs relation 제거+모델 단독(B). "좋은 모델이면 relation 층이 복잡도값을 하나"를 eval로 결정한다. 미구현·eval 없음.
8. `08-answer-body-synthesis-layer.md`
   사용자 답변 문장(body)을 답변 호출에서 떼어, certification으로 value·evidence·state를 확정한 뒤 맨 끝 LLM 호출이 그 확정 데이터를 종합해 답변을 만든다. body가 payload와 어긋나는 문제를 고치되, body는 확정 결과를 말로 옮길 뿐 state를 못 바꾼다(`04` 가드레일). 미구현·eval 없음.

## 왜 지금

현재 observation/report 흐름은 질문 실행 뒤 `run.json`, observation JSONL, `report.html`을 함께 확인하게 해준다. 이제 필요한 것은 관찰 도구를 더 키우는 일이 아니라, 그 관찰을 통해 확인된 실패를 product 동작 개선으로 연결하는 일이다.

Agoda 개선 분석은 sample fixture run을 기준으로 삼지 않는다. sample text fixture를 임시 PDF로 만들어 product API를 호출하는 실행은 runner smoke나 report 렌더링 확인에는 쓸 수 있지만, Agoda 원문 PDF 개선의 근거가 될 수 없다.

`02`의 final run인 `09`에서는 source unit 후보가 크게 개선됐지만, 남은 실패가 모두 retrieval 부재로 설명되지는 않는다. 예를 들어 특별 요청 질문은 조건 문맥을 담은 후보가 이미 retrieval 결과에 있는데도 value-only 후보만 근거로 supported가 만들어졌다. 즉 이 실패는 "후보를 못 찾은" coverage 문제가 아니라, 찾은 조건을 안 쓰고 값만으로 확정한 의미 판단 문제다. 따라서 다음 순서는 후보를 더 많이 찾는 일이 아니라, (1) LLM 답변 후보가 자기 답을 자기 인증하지 못하게 코드가 final state를 소유하고(`04`), (2) "이 값을 좌우하는 조건이 있는가"의 의미 판단은 LLM/relation extractor가 역할로 내고 코드가 그 역할 구조를 읽게 하는(`06`) 일이다. 코드가 그 의미 판단을 `kind`·page 근접 같은 구조 프록시로 흉내 내면 실제 1~2장 문서에서 무관한 값까지 강등된다는 것을 `04` 첫 구현 측정에서 확인했다(`docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`).

## 중심 흐름

```text
원문 Agoda PDF 실행
-> report/observation으로 실패 유형 분류
-> 첫 product 개선: source unit 구조화
-> 측정 재현성 preflight
-> LLM answer candidate와 final answer 분리 (04)
-> code certification이 구조 사실(grounding·value-grounding)로 ceiling을 강제 (04)
-> 의미 층이 값↔조건 역할 구조를 만들고 code certification이 그 역할을 읽어 state 결정 (06)
-> final state에서 사용자-facing body 생성
-> role별 후보 coverage 개선과 missing 원인 구분 (05)
-> 같은 원문 PDF 질문셋으로 before/after 확인
```

## 단계 경계

04 이후의 product 흐름은 아래 경계를 기준으로 다시 잡는다. 각 단계는 자기가 받은 것만 가지고 일하고, 다음 단계의 책임을 앞당겨 맡지 않는다.

| 단계 | 하는 일 | 만들지 않는 것 |
| --- | --- | --- |
| 검색 (05) | role별 source unit 후보를 찾고 locator/kind/provenance를 보존한다 | final state, 의미 판정, 사용자-facing 문장 |
| LLM 후보 | 값/claim 후보, evidence ref, 헷갈리는 점을 만든다 | final `supported`/`needs_review`, final body |
| 의미 층·관계 추출 (06) | 후보들 사이의 역할을 만든다 — 어떤 근거가 값이고, 어떤 caveat가 그 값을 좌우하며, 필요한 조건 역할이 비었는가 | final state(상태 확정은 코드 몫), 새 값 |
| code certification (04) | 구조 사실(grounding·value-grounding)과 의미 층이 만든 역할 구조를 읽어 final state를 정한다 | `kind`·page 근접으로 조건을 추정, 질문/답변 단어를 읽은 의미 추측 |
| final body | certified state와 facts를 사용자 문장으로 푼다 | state 승격, 새 값 생성 |

이 경계가 막아야 하는 버그는 네 가지다. 앞 셋은 위험한 쪽(confident-wrong)으로, 넷째는 그 반대쪽(과잉 강등)으로 무너지는 실패다.

- LLM이 자기 답을 자기가 인증하는 버그
- 코드가 질문이나 답변 키워드로 의미를 분류하는 버그
- final body가 state와 반대로 확정처럼 말하는 버그
- 코드가 `kind`·page 근접 같은 구조 프록시로 "조건이 값에 걸린다"를 추정해, 실제 문서에서 무관한 값까지 강등하는 버그

## 공유 규칙

- product code는 eval dataset, runner, run artifact를 import하거나 읽지 않는다.
- eval runner는 product API entry point를 호출한다. runner 내부에서 답을 만들거나 fixture expected value를 product result처럼 쓰지 않는다.
- Agoda 개선 분석용 run은 원문 PDF 입력만 사용한다. sample fixture run은 smoke 확인으로만 다룬다.
- `run.json`과 `report.html`은 보조 관찰 장치다. product 개선의 중심은 자료가 source unit, retrieval candidate, answer/evidence로 이어지는 흐름이다.
- 업체명이나 특정 질문 문구에 맞춘 예외처리로 답을 만들지 않는다.
- lexical rule은 후보 recall이나 구조 감지 보조로 쓸 수 있지만, 답변을 직접 만드는 하드코딩으로 쓰지 않는다.
- supported 상태는 evidence snippet과 source reference 없이는 성립하지 않는다.
- LLM output은 certification 전까지 후보이며, final answer/state가 아니다.
- code certification은 질문이나 답변의 free text keyword에 의존하지 않는다. 코드가 강제하는 판정 기준은 grounding/value-grounding 같은 구조 사실과 의미 층(`06`)이 만든 역할 구조이고, "조건이 값을 좌우하는가"를 `kind`·page 근접으로 추정하지 않는다.
- 구조 신호가 없거나 애매하면 위험한 쪽인 supported가 아니라 needs_review 또는 missing으로 간다.
- final body는 certified state 뒤에서만 만들고 state를 승격하지 않는다.
- 값만 있고 그 값을 좌우하는 조건이 함께 있는 정보는 supported로 단정하지 않는다. 단 이 판정의 주체는 의미 층(`06`)이 만든 역할 구조이며, 코드가 단독으로 `kind`·page 근접으로 흉내 내지 않는다(근거: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`).
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## 상위 Acceptance Criteria

1. 원문 PDF run과 sample fixture smoke run의 목적이 문서와 report에서 섞이지 않는다.
2. 원문 PDF baseline에서 8개 질문의 실패를 source unit, retrieval, answer composer, 상태 검증 중 어디에 가까운지 읽을 수 있다.
3. 첫 product 개선은 source unit 구조화에 집중하고, 같은 원문 PDF 질문셋으로 before/after를 비교한다.
4. `02` 이후 before/after는 실행 조건, 코드 버전, 반복 실행 여부를 함께 보고 해석한다.
5. source unit 구조화 뒤에도 남는 실패는 measurement noise, answer certification boundary, 근거 관계(의미) 추출, retrieval coverage 중 어디에서 생기는지 이어서 분류할 수 있다.
6. 개선 결과는 `run.json` 필드 증가가 아니라 answer/evidence path 변화와 근거 부족한 supported 감소로 확인한다.

## Slice 순서

이 묶음의 다음 작업은 아래를 기본으로 삼는다. 각 단계는 같은 원문 PDF 질문셋으로 다시 실행해 before/after evidence path를 읽은 뒤 다음 단계로 넘어간다. 문서 번호와 구현 우선순위의 관계는 표 아래에 적는다.

| 순서 | 문서 | 핵심 질문 | 다음 단계로 넘어가는 신호 |
| --- | --- | --- | --- |
| 0 | `01-original-pdf-observation-baseline.md` | 원문 PDF baseline을 믿고 읽을 수 있는가 | production-like run에서 candidate/evidence/status를 질문별로 볼 수 있다 |
| 1 | `02-source-unit-structure-improvement.md` | 원문이 질문 가능한 source unit으로 들어오는가 | 완료: `09`에서 라벨-값, 정책, 비용, 요청 단위가 source unit/candidate로 보인다 |
| 2 | `03-measurement-reproducibility-preflight.md` | 이후 before/after를 noise와 구분할 수 있는가 | 완료: run artifact가 commit/runtime/repeat/seed 조건을 드러내고 단일 run을 과신하지 않는다 |
| 3 | `04-answer-certification-boundary.md` | LLM 후보가 자기 답을 자기 인증하지 못하는가 | 구현됨: candidate↔certification↔final body가 분리되고, 코드가 grounding/value-grounding으로 ceiling을 강제한다. 조건-좌우 판단은 `06`으로 재귀속 |
| 4 | `05-subrequest-retrieval-coverage.md` | role별 후보를 더 잘 받고 missing 원인을 구분하는가 | role별 후보 경로와 missing 원인이 보이고, 후보가 값만/조건도 담는지 `06`에 넘길 수 있다 |
| 5 | `06-evidence-relation-extraction.md` | 값을 좌우하는 조건이 있을 때 표현·키워드와 무관하게 안정적으로 needs_review로 가는가 | 의미 층이 값↔조건 역할을 내고 코드가 읽어, P1-01이 paraphrase에도 needs_review로 간다 |
| 6 | `07-relation-vs-model-upgrade-ab.md` | 좋은 모델이면 relation 층이 복잡도값을 하나, 모델 단독이 나은가 | A(relation+강한 모델)·B(모델 단독)를 eval로 비교해 relation 층 유지/제거를 결정한다 |
| 7 | `08-answer-body-synthesis-layer.md` | 답변 문장(body)이 확정 payload와 일치하나 | body를 끝 LLM 합성으로 옮겨 state·evidence와 어긋나지 않고 초안 잔재(틀린 label·placeholder)가 안 샌다 |

문서 번호는 retrieval -> 의미 -> certification의 pipeline 위치 순서다. 다만 구현 우선순위에서는 `06`이 먼저다 — `06`은 알려진 위험 실패(P1-01)를 안정적으로 막는 binding fix이고, P1-01의 조건 후보는 이미 retrieval에 들어와 있어 `05`(coverage) 완성을 기다리지 않아도 그 케이스로 구현·검증할 수 있다. `05`는 조건 후보가 실제로 빠지는 compound question을 위한 coverage 일반화다. `07`·`08`은 `06` 결과 이후의 후속 결정(`07`: relation 층 유지/제거)과 개선(`08`: body 합성 분리)이다.

prompt 수정은 `04`의 product contract가 잡힌 뒤에 다룬다. 입력 source unit과 retrieval candidate가 넓고 흐릿한 상태에서 prompt만 고치는 것은 이 묶음의 기본 해법이 아니다.

## 이번 묶음에서 섞지 않는 범위

- Agoda 전용 parser나 질문별 하드코딩 답변을 만들지 않는다.
- source unit 구조화가 되기 전에 prompt 수정만으로 점수를 올리려 하지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 원본 PDF bytes나 raw provider payload를 `run.json` 또는 shared docs에 그대로 보존하지 않는다.
- LangSmith payload 정책을 바꾸지 않는다.

## 다음 slice 후보

source unit 구조화와 측정 preflight는 `02`~`03`에서 닫았고, `04`는 구현됐다. 남은 product 작업은 아래와 같다(구현 우선순위는 `06` 먼저, 위 Slice 순서 참고).

- `04-answer-certification-boundary.md`(구현됨): LLM answer candidate와 final answer를 분리하고, code certification이 grounding/value-grounding 같은 구조 사실로 ceiling을 강제한다. 조건-좌우 의미 판단은 `06`으로 재귀속.
- `06-evidence-relation-extraction.md`: 이미 후보에 들어온 값과 caveat의 역할·관계를 LLM/relation extractor가 만들어, 코드가 그 역할 구조를 읽고 P1-01을 안정적으로 needs_review로 보낼 수 있게 한다.
- `05-subrequest-retrieval-coverage.md`: 조건 후보가 실제로 빠지는 compound question에서 role별 후보를 더 잘 공급하고 missing 원인(source unit 부재 / retrieval miss / relation extraction miss)을 읽을 수 있게 한다.
- `07-relation-vs-model-upgrade-ab.md`: `06` 정밀도 천장 이후, relation 층 유지+강한 모델(A)과 relation 제거+모델 단독(B)을 eval로 비교해 relation 층의 값어치를 결정한다.
- `08-answer-body-synthesis-layer.md`: 답변 문장(body)을 certification 뒤 끝 LLM 합성으로 분리해, body가 확정 state·evidence와 일치하고 초안 잔재가 안 새게 한다.

## 남은 판단

- 원문 PDF 파일을 repo fixture로 보존할지, repo에 보존하지 않는 외부 입력 경로만 지원할지는 별도 판단이다.
- source unit `kind`, evidence role, answer candidate field name의 정확한 값 목록은 구현 시 현재 자료 모델과 retrieval needs에 맞춰 정한다.
- source cue / answer cue의 정확한 JSON field name은 runner와 질문셋 수정 시 정한다.
