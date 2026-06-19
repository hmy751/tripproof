# Original PDF observation baseline

작성일: 2026-06-19

상태: draft sub-spec. Agoda 개선을 시작하기 전에 원문 PDF로 현재 product behavior를 확인하고, 실패 유형을 분류하기 위한 기준이다.

이 문서는 product 개선 자체가 아니다. 개선 전 상태를 제대로 읽기 위한 baseline이다. 여기서 얻은 실패 분류가 다음 문서의 source unit 구조화 개선으로 이어진다.

## 목적

원문 Agoda PDF와 `eval/datasets/agoda-booking-confirmation/questions.json`을 product API에 넣어 현재 QA 실패를 확인한다. report는 질문별 retrieval candidate, composer context, answer item/evidence를 보여줘야 한다.

sample fixture run은 이 baseline이 아니다. sample fixture는 runner smoke나 report 렌더링 확인에는 쓸 수 있지만, Agoda 원문 PDF 개선 근거로 해석하지 않는다.

## 관찰할 것

질문별 실패는 하나의 정답 라벨로 고정하지 않는다. 다만 다음 네 가지 관점으로 읽을 수 있어야 한다.

| 관점 | 의미 | report에서 볼 단서 |
| --- | --- | --- |
| Source unit | 원문 PDF가 질문 가능한 의미 단위로 나뉘지 않았다 | 필요한 정보가 큰 덩어리 안에 묻히거나 별도 candidate로 보이지 않는다 |
| Retrieval | 필요한 source unit이 있는데 후보로 올라오지 않았다 | correct-looking unit이 낮은 순위이거나 candidate 목록에 없다 |
| Answer composer | 근거는 왔는데 답변 조립이 틀렸다 | evidence는 보이지만 answer item/status가 빗나간다 |
| State validation | supported/unsupported 판단이 근거 상태와 맞지 않는다 | 조건 문맥 없이 supported가 되거나, 근거가 있는데 unsupported가 된다 |

분류는 중복될 수 있다. 예를 들어 source unit이 너무 크면 retrieval과 answer composer 실패처럼 함께 보일 수 있다. 이 문서의 역할은 책임 소재를 하나로 고정하는 것이 아니라, 먼저 고칠 product 면을 고를 만큼 실패를 읽게 하는 것이다.

## Run 기준

- 입력은 사용자가 제공한 원문 Agoda PDF다.
- 실행은 product API entry point를 통한다.
- 질문셋은 `eval/datasets/agoda-booking-confirmation/questions.json`을 사용한다.
- 원문 PDF baseline은 가능한 한 production runtime과 같은 조건으로 실행한다. 기본은 실제 answer composer, 실제 embedding provider/generation, 설정된 retrieval backend를 타야 하며, deterministic fake embedding이나 `missing` composer는 baseline이 아니라 smoke/test double 실행으로만 명시한다.
- runner가 테스트 편의를 위해 deterministic mode를 제공하더라도 opt-in이어야 한다. `run.json`과 report는 production-like 실행인지 deterministic smoke인지 구분해 기록한다.
- `run.json`은 실행 조건과 결과를 남기는 원장이다. product result가 아니며, product response body에 observation/debug/eval field를 추가하지 않는다.
- HTML report는 사람이 실패 유형을 읽기 위한 보기다. report가 답을 새로 만들거나 product 판단을 덮어쓰지 않는다.

## 최신 baseline artifact

- Run folder: `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/`
- Report: `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/report.html`
- Run JSON: `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/run.json`
- Observation JSONL: `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/observations/observation-export.jsonl`

이 run은 `mode=production`, `production_like=true`, `retrieval_backend=supabase`, `embedding_provider=ollama`, `embedding_model=nomic-embed-text-v2-moe`, `answer_composer=ollama`, `answer_model=gemma3:4b` 조건으로 실행했다.

관찰 결과:

- request/correlation id, observation export, product response contamination check는 정상이다.
- 8개 질문의 rule check는 모두 실패했다.
- 원문 PDF는 1 page로 파싱됐고, source unit은 2개만 생성됐다.
- 모든 질문에서 retrieval candidate가 사실상 같은 두 큰 source unit에 집중된다.
- 일부 질문은 필요한 단서가 context 안에 있어도 answer composer가 일부 값만 뽑거나 evidence state를 오판했다.

## Acceptance Criteria

1. 원문 PDF path를 받은 실행과 sample fixture smoke 실행의 목적이 report 또는 실행 기록에서 구분된다.
2. 원문 PDF 실행 뒤 8개 질문 각각에 대해 retrieval candidate, evidence, answer item/status를 report에서 확인할 수 있다.
3. 각 실패 질문은 source unit, retrieval, answer composer, 상태 검증 중 어디가 의심되는지 사람이 분류할 수 있다.
4. `run.json`은 실행 조건과 결과를 남기되, product 응답을 대신하거나 fixture expected value를 product result처럼 쓰지 않는다.
5. product response body에는 observation/debug/eval field가 추가되지 않는다.
6. 원문 PDF baseline의 실행 기록은 `answer_composer`, `embedding_provider`, `retrieval_backend`, runtime mode를 보여주며, production-like가 아닌 실행은 baseline으로 해석하지 않게 표시된다.

## 확인 방법

1. 원문 Agoda PDF path와 `questions.json`으로 production-like baseline run을 만든다.
2. report에서 8문항을 열어 candidate, evidence, answer/status를 확인한다.
3. 실패 질문을 source unit, retrieval, answer composer, 상태 검증 관점으로 분류한다.
4. sample fixture run이 있다면 smoke 성격으로만 표시되고, Agoda improvement baseline으로 읽히지 않는지 확인한다.
5. `run.json`의 runtime이 deterministic fake embedding이나 `missing` composer를 쓰지 않았는지 먼저 확인한다. 부득이하게 production과 다른 backend를 썼다면 그 run은 해당 차이를 전제로만 해석한다.

## 이번 문서에서 섞지 않는 범위

- source unit 구조화 구현은 `02-source-unit-structure-improvement.md`가 다룬다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 원본 PDF bytes나 raw provider payload를 `run.json` 또는 shared docs에 그대로 보존하지 않는다.
- LangSmith payload 정책을 바꾸지 않는다.
