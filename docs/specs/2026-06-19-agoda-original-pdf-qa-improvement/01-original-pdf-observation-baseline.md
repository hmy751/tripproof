# Original PDF observation baseline

작성일: 2026-06-19

상태: baseline 확정(현재 before 기준 = `agoda-original-pdf-baseline-postreconcile-20260623-production`). 실패 분류 기준은 draft 유지. Agoda 개선을 시작하기 전에 원문 PDF로 현재 product behavior를 확인하고, 실패 유형을 분류하기 위한 기준이다.

이 문서는 product 개선 자체가 아니다. 개선 전 상태를 제대로 읽기 위한 baseline이다. 여기서 얻은 실패 분류가 다음 문서의 source unit 구조화 개선으로 이어진다.

## 목적

원문 Agoda PDF와 `eval/datasets/agoda-booking-confirmation/questions.json`을 product API에 넣어 현재 QA 실패를 확인한다. report는 질문별 retrieval candidate, composer context, answer item/evidence를 보여줘야 한다.

sample fixture run은 이 baseline이 아니다. sample fixture는 runner smoke나 report 렌더링 확인에는 쓸 수 있지만, Agoda 원문 PDF 개선 근거로 해석하지 않는다.

## 관찰할 것

질문별 실패는 하나의 정답 라벨로 고정하지 않는다. 다만 다음 네 가지 관점으로 읽을 수 있어야 한다.

| 관점 | 의미 | report에서 볼 단서 |
| --- | --- | --- |
| Source unit | 원문 PDF가 질문 가능한 의미 단위로 나뉘지 않았다 | 필요한 정보가 큰 덩어리 안에 묻히거나 별도 candidate로 보이지 않는다 (`char_length`, `locator`, `kind`) |
| Retrieval | 필요한 source unit이 있는데 후보로 올라오지 않았다 | correct-looking unit이 낮은 순위이거나 candidate 목록에 없다 (`candidate_count`, `score`, `lexical_score`/`vector_score`) |
| Answer composer | 근거는 왔는데 답변 조립이 틀렸다 | evidence는 보이지만 answer item/status가 빗나간다 (`items`, `evidence`) |
| State validation | `evidence_state`(supported / missing / needs_review 등) 판단이 근거 상태와 맞지 않는다 | 조건 문맥 없이 supported가 되거나, 근거가 있는데 missing/needs_review로 빠진다 (`evidence_state_counts`) |

질문셋의 `expected_evidence_state`는 supported 한 가지가 아니라 missing, needs_review도 섞여 있고, 채점은 `state_matched`로 이 다값을 비교한다. State validation은 supported/unsupported 이진이 아니라 다값 상태 검증으로 본다.

분류는 중복될 수 있다. 예를 들어 source unit이 너무 크면 retrieval과 answer composer 실패처럼 함께 보일 수 있다. 이 문서의 역할은 책임 소재를 하나로 고정하는 것이 아니라, 먼저 고칠 product 면을 고를 만큼 실패를 읽게 하는 것이다.

## Run 기준

- 입력은 사용자가 제공한 원문 Agoda PDF다.
- 실행은 product API entry point를 통한다.
- 질문셋은 `eval/datasets/agoda-booking-confirmation/questions.json`을 사용한다.
- 원문 PDF baseline은 가능한 한 production runtime과 같은 조건으로 실행한다. 기본은 실제 answer composer, 실제 embedding provider/generation, 설정된 retrieval backend를 타야 하며, deterministic fake embedding이나 `missing` composer는 baseline이 아니라 smoke/test double 실행으로만 명시한다.
- runner가 테스트 편의를 위해 deterministic mode를 제공하더라도 opt-in이어야 한다. `run.json`과 report는 production-like 실행인지 deterministic smoke인지 구분해 기록한다.
- `run.json`은 실행 조건과 결과를 남기는 원장이다. product result가 아니며, product response body에 observation/debug/eval field를 추가하지 않는다.
- HTML report는 사람이 실패 유형을 읽기 위한 보기다. report가 답을 새로 만들거나 product 판단을 덮어쓰지 않는다.

## 측정 timeline과 현재 baseline

이 baseline은 한 번의 측정이 아니라 이어진 측정 흐름이다. 같은 원문 PDF와 같은 8문항을 같은 production-like 조건으로 세 시점에 걸쳐 돌렸고, 각 run은 역할이 다르다.

| 시점 | run | 역할 |
| --- | --- | --- |
| 2026-06-19 시작 baseline | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/` | layout 개선 전 시작점. source unit 구조 문제를 드러낸 근거 |
| 2026-06-19 layout v1 after | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/` | `02`의 source unit 구조화가 baseline을 어떻게 바꿨는지 본 측정 |
| 2026-06-23 현재 baseline | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/` | reconciliation 이후 같은 조건 재측정. 지금 before 기준으로 삼는 current baseline |

세 run의 runtime config는 동일하다: `mode=production`, `production_like=true`, `retrieval_backend=supabase`, `retrieval_top_k=3`, `retrieval_similarity_threshold=0.0`, `embedding_provider=ollama`, `embedding_model=nomic-embed-text-v2-moe`(`embedding_dimensions=768`, `embedding_auto_generate=true`), `answer_composer=ollama`, `answer_model=gemma3:4b`. 같은 config라야 시점 간 차이를 substrate/구현 변화로 읽을 수 있다. 아래 개별 run 절은 config를 다시 나열하지 않고 artifact 경로와 그 run 고유의 관찰만 둔다.

### 시작 baseline에서 본 것 (2026-06-19)

- 원문 PDF는 1 page로 파싱됐고, source unit은 `2`개만 생성됐다.
- 모든 질문에서 retrieval candidate가 사실상 같은 두 큰 source unit에 집중된다.
- 8개 질문의 rule check는 모두 실패(`0/8`)했고, evidence state match는 `2/8`이었다.
- 일부 질문은 필요한 단서가 context 안에 있어도 answer composer가 일부 값만 뽑거나 evidence state를 오판했다.

구조 사실(`source_unit_count=2`)이 retrieval 집중과 점수 실패의 원인으로 읽힌다. 이 시작점이 `02-source-unit-structure-improvement.md`의 source unit 구조화로 이어졌다. layout v1 적용 결과와 before/after 해석은 `02`에서 다룬다.

### 현재 baseline (2026-06-23)

현재 before 기준은 이 2026-06-23 post-reconcile run이다. layout v1을 main refactor(`refactor/server-dx-cleanup`, `docs/engineering`)와 통합(merge `4a51ebe`)한 뒤, 같은 원문 PDF·같은 8문항을 다시 측정했다.

- Run folder: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/`
- Report: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/report.html`
- Run JSON: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/run.json`
- Observation JSONL: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/observations/observation-export.jsonl`

관찰 결과:

- request/correlation id, observation export, product response contamination check는 정상이다.
- layout v1이 반영되어 source unit은 `40`개다(`02`의 layout chunking은 결정적이라 시작 baseline의 `2`개에서 늘어난 값이 그대로 유지된다).
- 8개 질문의 rule check는 여전히 모두 실패(`0/8`)다.
- evidence state match는 `3/8`이며, 일치 항목은 `checkin_action`, `missing_checkin_start_time`, `room_and_party`다.
- 조건 문맥이 중요한 항목(`cancellation_policy`, `on_site_extra_costs`, `special_request_boundary` 등)은 값과 조건을 함께 잡지 못해 여전히 실패한다.

세 시점 state match는 시작 `2/8` -> layout v1 `4/8` -> current `3/8`로 움직였다. source unit은 layout v1 이후 `40`개로 불변이므로, current가 layout v1보다 한 항목 적은 것은 구조 후퇴가 아니다. layout v1과 current의 retrieval candidate는 질문별로 동일했고(같은 source unit index·순위·score), 달라진 것은 같은 context를 받은 `gemma3:4b` answer composer 출력뿐이다. 이 차이의 자세한 해석은 `02`의 V1 구현 결과에서 같은 timeline으로 정리한다.

reconciliation 중 runner 기본 env의 graft(placeholder Supabase, `EMBEDDING_AUTO_GENERATE=0`)를 제거해 production이 실제 `.env` config를 타도록 정정했다. 다만 이 정정은 runner 기본 env 경로를 바로잡은 일이고, 세 production 라벨 run의 기록 runtime은 시작/after/current 모두 동일하게 supabase + ollama embedding/answer로 남아 있다. 즉 graft 제거는 06-23 state match 차이의 원인이 아니다.

같은 8문항이 source unit 구조화 뒤에도 rule을 통과하지 못하므로, 다음 작업(`03`~`05`)은 여전히 유효하다.

> 참고: 이 06-23 post-reconcile run을 현재 before 기준으로 삼는다. 상위 `index.md`와 `02`도 같은 run을 current baseline으로 가리킨다.

## Acceptance Criteria

1. 원문 PDF path를 받은 실행과 sample fixture smoke 실행의 목적이 report 또는 실행 기록에서 구분된다.
2. 원문 PDF 실행 뒤 8개 질문 각각에 대해 retrieval candidate, evidence, answer item/status를 report에서 확인할 수 있다.
3. 각 실패 질문은 report의 `Evidence path`에 실재하는 단서(candidate locator/`score`/`lexical_score`, context block, answer item의 `evidence_state`/`evidence_state_counts`)를 근거로 source unit, retrieval, answer composer, 상태 검증 네 관점 중 최소 하나를 지목할 수 있다.
4. `run.json`은 실행 조건과 결과를 남기되, product 응답을 대신하거나 fixture expected value를 product result처럼 쓰지 않는다.
5. product response body에는 observation/debug/eval field가 추가되지 않는다.
6. 원문 PDF baseline의 실행 기록은 `answer_composer`, `embedding_provider`, `retrieval_backend`, runtime mode를 보여주며, production-like가 아닌 실행은 baseline으로 해석하지 않게 표시된다.

## 확인 방법

1. 원문 Agoda PDF path와 `questions.json`으로 production-like baseline run을 만든다.
2. report에서 8문항을 열어 candidate, evidence, answer/status를 확인한다.
3. 실패 질문을 source unit, retrieval, answer composer, 상태 검증 관점으로 분류한다.
4. sample fixture run이 있다면 smoke 성격으로만 표시되고, Agoda improvement baseline으로 읽히지 않는지 확인한다.
5. `run.json`의 runtime이 deterministic fake embedding이나 `missing` composer를 쓰지 않았는지 먼저 확인한다. 부득이하게 production과 다른 backend를 썼다면 그 run은 해당 차이를 전제로만 해석한다.
6. 시점 간 baseline 수치를 비교할 때는 세 run의 runtime config(backend/embedding/top_k/threshold/composer)가 같은지 먼저 확인하고, 차이가 있으면 그 차이를 전제로만 수치를 비교한다.

## 이번 문서에서 섞지 않는 범위

- source unit 구조화 구현은 `02-source-unit-structure-improvement.md`가 다룬다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 원본 PDF bytes나 raw provider payload를 `run.json` 또는 shared docs에 그대로 보존하지 않는다.
- LangSmith payload 정책을 바꾸지 않는다.
