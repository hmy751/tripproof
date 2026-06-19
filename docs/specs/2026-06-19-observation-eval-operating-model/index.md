# Observation / eval operating model

작성일: 2026-06-19

상태: 후속 구현 기준 spec. 현재 `run.json`, local observation JSONL, LangSmith, future HTML report의 책임 경계와 local rich observation 보강 방향을 정리한다. 이 문서는 구현 완료나 eval 개선 결과를 주장하지 않는다.

## 왜 지금

TripProof는 product path 실행 중 internal observation record를 만들고, 이를 local observation artifact나 LangSmith로 내보낸다. eval runner는 product API를 호출하고 `run.json`에 실행 결과를 남긴다. 이 구조의 방향은 맞지만, 개발자가 실제 실패를 볼 때는 다음 질문이 바로 풀리지 않는다.

- `run.json`, observation JSONL, config snapshot, LangSmith trace 중 무엇을 먼저 봐야 하는가.
- eval이 observation을 소유하는 것처럼 보이지 않게 하면서도, HTML report에서 둘을 함께 보여줄 수 있는가.
- observation이 count 중심이면 retrieval 후보와 answer item의 실제 내용을 어떻게 확인할 수 있는가.
- local observation에는 판단 경로의 전문을 넣어도 되는가, 그렇다면 어디까지 넣어야 하는가.
- LangSmith는 같은 전문을 기본으로 가져가야 하는가.

이번 기준은 privacy/redaction을 중심으로 삼지 않는다. 중심은 개발자 경험과 책임 경계다. 다만 raw dump가 product response나 외부 trace provider의 기본 payload로 번지는 것은 막는다.

## 개발자 장면

개발자가 예약 확인서 질문셋을 실행했는데 여러 질문이 `missing`이거나 잘못된 `supported`로 나온다. 개발자는 eval summary에서 실패 질문을 고르고, 그 질문에서 실제로 검색 후보로 오른 SourceUnit 전문, answer composer에 전달된 context, 생성된 answer item/evidence를 바로 보고 싶다.

이때 개발자가 보는 순서는 다음과 같아야 한다.

```text
eval run / HTML report
  -> 실패 질문과 rule check 확인
  -> correlation_id로 runtime observation drill-down
  -> selected retrieval candidate 전문과 answer item/evidence 확인
  -> 필요하면 LangSmith에서 같은 operation/step tree 확인
```

product API response는 여전히 사용자-facing 결과만 반환한다. observation이나 eval 결과가 response body에 섞이면 안 된다.

## 핵심 모델

| 층위 | 소유하는 것 | 소유하면 안 되는 것 |
| --- | --- | --- |
| Product result | `/api/materials`, `/api/questions` response와 화면 상태 | observation/debug/runtimeConfig/eval pass-fail |
| Runtime observation | product 실행 중 실제로 생긴 단계, 선택, 탈락, config, 후보, answer projection | eval expected state, required cue, rule pass/fail |
| Eval run | fixture, 질문셋, 기대값, product response, rule check, run summary | product observation schema, product runtime 판단 |
| HTML report | eval run과 observation을 사람이 읽게 join한 view | 새로운 source of truth |
| LangSmith | observation export를 외부 trace UI로 투영한 view | product/eval 판정 기준, observation schema 소유권 |

간단히 말하면 eval은 observation을 읽고 연결할 수 있지만, observation의 의미를 정의하지 않는다. observation은 product runtime이 소유하고, eval은 product behavior를 관찰한다.

## Goal

- 개발자는 eval 실행 뒤 `run.json` 또는 HTML report에서 실패 질문을 먼저 고를 수 있다.
- 실패 질문 detail은 같은 `correlation_id`의 runtime observation을 보여주되, eval expected/pass-fail과 runtime facts를 구분한다.
- local observation artifact는 count만이 아니라 질문 판단 경로에 오른 전문을 포함할 수 있다.
- 전문 포함은 "전체 원문 저장"이 아니라 "그 단계가 실제로 선택하거나 생성한 대상"으로 제한한다.
- LangSmith는 기본적으로 summary projection을 유지한다. 전문 전송은 별도 explicit option이나 후속 판단으로 둔다.
- product response body는 기존처럼 사용자-facing 결과만 담는다.

## Rules

- product code는 eval runner, eval fixture, eval run artifact를 import하거나 읽지 않는다.
- eval runner는 product API를 호출하고, `correlation_id`로 observation export를 연결한다.
- `run.json`에는 eval 기대값, product response, rule check, observation 위치와 요약을 둔다.
- observation에는 product runtime에서 실제로 일어난 단계, 선택, 생성 결과, failure kind, runtime config snapshot을 둔다.
- observation에는 eval expected state, required evidence cue, rule pass/fail, priority 같은 eval-only 기준을 넣지 않는다.
- HTML report는 `run.json`과 observation JSONL을 join해서 보여주는 view다. report가 별도 truth source가 되면 안 된다.
- local observation artifact는 개발자 디버깅용으로 rich text를 담을 수 있다.
- LangSmith는 같은 envelope를 소비하더라도 기본 payload는 summary 중심으로 둔다.
- product response body에는 `observation`, `debug`, `runtimeConfig`, `traceId`, `requestId`, `correlationId`, `eval` field를 추가하지 않는다.

## 전문 포함 기준

전문을 넣는 기준은 "바로 원인 분석에 필요한가"다. 넣는 대상은 각 단계가 실제로 선택하거나 생성한 값이어야 한다.

| 단계 | 넣을 수 있는 전문 | 넣지 않는 것 |
| --- | --- | --- |
| material upload | 작은 문서나 local rich mode에서 SourceUnit text, locator, char length, kind | 원본 PDF bytes, 파싱 전 raw blob, 모든 자료의 반복 덤프 |
| source unit build | 생성된 SourceUnit의 id, locator, text, char length. 큰 문서는 전체가 아니라 후속 question path에서 선택된 unit 중심 | 전체 document archive를 observation마다 중복 저장 |
| retrieval | top-k candidate의 source_unit_id, locator, score, source unit text | retrieval 대상 전체 SourceUnit 목록 |
| context assembly | answer composer에 실제 전달된 context block 전문 | 후보였지만 전달되지 않은 모든 원문 |
| answer projection | answer item의 label/body/value/evidence state, evidence snippet, evidence source_unit_id/locator | raw LLM request/response 전체 |
| failure/missing | 실패한 단계의 입력/후보 전문과 product failure reason | eval expected/pass-fail, stack trace, provider raw payload |

첫 보강은 question observation에 집중한다. 질문 실패를 분석할 때 가장 필요한 것은 해당 질문에서 선택된 retrieval candidate와 composer context, answer item/evidence이기 때문이다. material upload observation은 구조 요약을 유지하되, 작은 문서 또는 local rich mode에서만 source unit text를 포함하는 쪽이 안전하다.

## Local rich observation

현재 local observation artifact는 export-safe projection을 기준으로 한다. 후속 구현에서는 local debugging을 위해 더 풍부한 projection을 추가할 수 있다.

```text
internal observation record
  -> summary export payload
      -> local JSONL
      -> LangSmith

internal observation record + selected text facts
  -> local rich observation payload
      -> local JSONL / HTML report
```

이때 "rich"는 eval-owned field가 아니라 product runtime fact의 더 자세한 local projection이다. 예를 들어 `candidate_summary`가 `candidate_count`만 갖는 대신, local rich payload에서는 selected candidates 배열을 가질 수 있다.

```json
{
  "candidate_count": 2,
  "candidates": [
    {
      "source_unit_id": "su_123",
      "locator": "page 1",
      "vector_score": 0.78,
      "lexical_score": 0,
      "text": "Cancellation: Any cancellation received within 1 day prior..."
    }
  ]
}
```

answer projection도 count만으로 끝내지 않고, product answer composer가 실제로 만든 item과 evidence를 local rich payload에서 볼 수 있어야 한다.

```json
{
  "items": [
    {
      "label": "특별 요청",
      "body": "NonSmoke, LargeBed 요청이 기록되어 있지만 확정 조건은 아닙니다.",
      "evidence_state": "needs_review",
      "evidence": [
        {
          "source_unit_id": "su_456",
          "locator": "page 1",
          "snippet": "All special requests are subject to availability..."
        }
      ]
    }
  ]
}
```

위 예시는 shape의 방향을 보여주는 것이며, 정확한 field name은 구현 시 현재 observation model과 serializer 책임에 맞춰 좁힌다.

## Eval run과 HTML report

`run.json`은 eval run의 machine-readable index다.

- 어떤 PDF와 questions file을 돌렸는가.
- 어떤 product entry point를 호출했는가.
- 어떤 runtime config에서 실행했는가.
- 각 질문의 expected state, product response, rule check는 무엇인가.
- observation export directory와 operation count는 무엇인가.
- 각 질문의 `correlation_id`는 무엇인가.

HTML report는 사람이 보는 eval run view다. report는 local rich observation을 복사해 새 truth로 삼지 않고, `run.json`과 observation JSONL을 읽어 질문 detail 화면에 함께 표시한다.

처음 HTML report가 보여줄 내용은 작게 시작한다.

- run summary: question count, passed rule checks, request failures, expected/observed evidence state counts.
- question list: id, priority, expected state, observed states, rule passed, missing cues, must-not hits.
- question detail: product answer summary/items/evidence, retrieval candidate text, composer context text, answer projection facts.
- drill-down: `correlation_id`, artifact-relative observation path/line, optional LangSmith project/search hint.

HTML report는 product response를 바꾸지 않고, eval runner가 observation schema를 소유하게 만들지도 않는다.

## LangSmith 역할

LangSmith는 `ObservationExportEnvelope`를 외부 trace UI로 보여주는 sink다. root run은 operation 하나에 대응하고, child runs/events는 observation step tree의 projection이다.

기본 LangSmith payload는 다음을 유지한다.

- operation, record id, request id, correlation id.
- final status, failure kind.
- step status/failure/facts summary.
- runtime config snapshot summary.
- retrieval/prompt/model 같은 검색용 metadata.

전문 text는 기본으로 LangSmith에 보내지 않는다. 외부 viewer에서 전문 확인이 필요해지면 `TRIPPROOF_LANGSMITH_INCLUDE_TEXT` 같은 explicit option이나 별도 adapter policy로 다시 판단한다. 이 판단 전까지는 local observation artifact와 HTML report가 rich text DX를 맡는다.

## 구현면 펼치기

| 구현면 | 필요한 이유 | 첫 기준 |
| --- | --- | --- |
| Question rich facts | 실패 질문에서 실제 retrieval 후보와 answer item을 바로 봐야 한다 | question observation local rich payload에 selected candidate text와 answer item/evidence가 있다 |
| Material source unit summary | source unit이 너무 크거나 적은 문제를 알아야 한다 | source unit count 외에 locator, char length, optional text를 볼 수 있다 |
| Eval/report join | eval 실패와 runtime observation을 한 화면에서 봐야 한다 | `correlation_id`로 `run.json` question과 observation record를 연결한다 |
| LangSmith policy | 외부 trace viewer가 observation schema를 끌고 가지 않아야 한다 | default LangSmith payload는 summary이고, text include는 별도 opt-in이다 |
| Docs/DX entry | 개발자가 어떤 파일을 먼저 볼지 알아야 한다 | eval README나 report가 `run.json -> observation -> LangSmith` 순서를 설명한다 |

## 먼저 고를 slice

첫 slice는 question observation local rich payload다.

```text
질문 실행
  -> retrieval selected candidates
  -> answer composer context
  -> answer item/evidence
  -> local observation JSONL
  -> eval report에서 correlation_id로 표시
```

이 slice는 product response를 바꾸지 않고, LangSmith payload도 기본적으로 바꾸지 않는다. eval expected/pass-fail은 `run.json`에만 남긴다.

## Acceptance criteria

1. question local rich observation은 selected retrieval candidate의 source_unit_id, locator, score, source unit text를 확인할 수 있어야 한다.
2. question local rich observation은 answer item의 label/body/value/evidence state와 evidence snippet/source reference를 확인할 수 있어야 한다.
3. observation payload에는 eval expected state, required cue, rule pass/fail이 들어가지 않아야 한다.
4. eval report는 `run.json`과 observation JSONL을 `correlation_id`로 join해 보여주되, observation schema의 owner가 되면 안 된다.
5. default product API response body와 default LangSmith summary payload는 rich local observation 때문에 바뀌지 않아야 한다.

## Non-goals

- product response에 raw source, answer body debug, observation, eval result를 추가하지 않는다.
- eval runner가 observation step schema를 정의하거나 product observation model을 import해 수정하지 않는다.
- raw PDF bytes, embedding vector, raw provider request/response, secret, stack trace를 저장하지 않는다.
- 모든 SourceUnit 전문을 모든 observation record에 반복 저장하지 않는다.
- LangSmith 전문 전송을 첫 slice로 하지 않는다.
- eval score threshold나 release gate를 확정하지 않는다.

## 현재 코드에서 볼 곳

- `apps/server/use_cases/questions.py`: question product path와 observation reporter 호출 순서.
- `apps/server/questions/observation.py`: question observation step, safe facts, answer projection facts.
- `apps/server/retrieval/search.py`: retrieval trace와 candidate selection.
- `apps/server/retrieval/models.py`: `AnswerContext`, `RetrievedSource`, `SourceUnit`.
- `apps/server/observations/serializers.py`: internal observation record를 export envelope로 projection하는 경계.
- `apps/server/observations/sinks.py`: local observation artifact writer와 fanout exporter.
- `apps/server/observations/langsmith.py`: LangSmith projection.
- `eval/run_question_dataset.py`: question dataset runner와 `run.json` 생성.
- `eval/question_runtime_recording_smoke.py`: correlation/export 연결 smoke runner.
- `eval/find_observation_by_correlation.py`: local observation lookup helper.

## 확인 방법 후보

- local rich observation이 꺼진 기존 경로에서 `/api/questions` response body가 동일한지 확인한다.
- question dataset run 뒤 `run.json`의 question id/correlation id와 observation JSONL question record가 연결되는지 확인한다.
- 실패 질문 detail에서 selected candidate text와 answer item/evidence를 수동으로 읽어 원인 분석이 가능한지 확인한다.
- LangSmith adapter 테스트에서 default payload가 text 전문을 포함하지 않는지 확인한다.

## 남은 판단

- local rich observation을 기존 `observation-export.jsonl`에 같은 schema version으로 additive하게 넣을지, 별도 file 또는 mode로 둘지.
- source unit text를 material upload observation에도 항상 넣을지, question path에서 선택된 unit만 우선 넣을지.
- large document에서 text payload 크기를 어떤 기준으로 제한할지.
- HTML report를 eval runner가 같이 만들지, 별도 renderer command로 둘지.
- LangSmith text opt-in을 언제, 어떤 env와 field policy로 열지.
