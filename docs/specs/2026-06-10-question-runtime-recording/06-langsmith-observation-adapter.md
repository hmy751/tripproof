# LangSmith observation adapter

작성일: 2026-06-11

상태: 구현된 하위 작업 spec. `observation_export.v1` payload를 LangSmith로 내보내는 adapter의 mapping contract를 정한다.

## 왜 지금

01-05에서 material upload와 question answer의 내부 observation record, runtime config snapshot, `observation_export.v1` payload, no-op/local artifact exporter가 닫혔다. 이제 LangSmith를 붙일 수 있지만, LangSmith SDK를 먼저 붙이면 외부 trace provider의 run shape가 내부 record나 export payload를 다시 끌고 갈 수 있다.

이 slice는 LangSmith를 product runtime의 관측 기준으로 올리는 일이 아니다. 내부 record와 local artifact exporter가 이미 소비하는 같은 `ObservationExportEnvelope`를 LangSmith에 맞게 안전하게 해석하는 계약만 정한다.

## 사용자 장면

사용자가 여행 자료를 업로드하고 자료함에 질문한다. API 응답은 기존처럼 material 또는 question response만 반환한다.

개발자는 LangSmith가 켜진 환경에서 다음을 확인할 수 있어야 한다.

- 어떤 operation export가 남았는가: `material_upload` 또는 `question_answer`.
- operation의 최종 상태와 failure kind가 무엇인가.
- parent/leaf step이 어떤 순서와 status로 닫혔는가.
- 실행 당시 runtime config snapshot이 무엇인가.
- LangSmith payload가 실행 조건과 원인 범주를 설명하는 신호 중심으로 유지됐는가.
- LangSmith 설정이 없거나 호출이 실패해도 product response가 바뀌지 않았는가.

## Goal

- LangSmith adapter는 내부 `MaterialUploadObservationRecord`나 `QuestionObservationRecord`를 직접 소비하지 않고 `observation_export.v1` envelope만 소비한다.
- `LangSmithObservationExporter`는 `ObservationExporter` 구현체 하나로 추가한다.
- LangSmith root run은 한 export envelope에 대응한다.
- parent/leaf step은 synthetic LangSmith child runs로 펼치고, root run의 ordered events와 metadata에도 남긴다.
- child run tree는 observation record tree를 보기 좋게 펼친 표현이며, step별 실제 latency를 의미하지 않는다.
- full runtime config snapshot은 root run metadata에 두고, child run에는 해당 step을 해석하는 데 필요한 runtime hint만 선별해 둔다.
- LangSmith input/output, event payload, metadata에는 실행을 다시 설명하는 데 필요한 진단 신호만 기본으로 넣는다.
- LangSmith env가 없거나 비활성화된 환경에서는 LangSmith sink만 꺼진다. local artifact sink가 설정되어 있으면 계속 동작한다.
- LangSmith 호출 실패는 material/question product response, material store 상태, 기존 exception propagation을 바꾸지 않는다.

## Rules

- LangSmith는 export sink다. observation record shape의 소유자가 되면 안 된다.
- adapter 입력은 `ObservationExportEnvelope`다. 구현에서 내부 record dataclass나 operation-specific recorder를 import해 mapping하면 안 된다.
- LangSmith root run name은 operation별로 안정된 machine-readable 이름을 쓴다.

| Operation | Root run name | Run type |
| --- | --- | --- |
| `material_upload` | `tripproof.material_upload` | `chain` |
| `question_answer` | `tripproof.question_answer` | `chain` |

- root run inputs는 safe summary만 둔다.

```text
inputs
  operation
  subject
```

- root run outputs는 final result summary만 둔다.

```text
outputs
  final_status
  failure_kind
```

- product 상태인 `failed` 또는 `blocked`를 LangSmith SDK/client failure로 해석하지 않는다. `final_status`와 `failure_kind`로 남기고, raw exception stack은 보내지 않는다.
- `answer_composer_failed`, `retrieval_failed`처럼 product path에서 예외가 있었던 failure kind도 처음에는 safe failure summary로만 보낸다. LangSmith `error` field를 쓰더라도 stack trace나 provider payload를 채우지 않는다.
- `LANGSMITH_TRACING` 같은 LangSmith 표준 tracing env만으로 adapter가 자동 활성화되면 안 된다. TripProof 쪽 explicit enable env가 있어야 한다.
- RunTree 같은 low-level API를 쓰는 구현은 LangSmith tracing env의 자동 on/off와 다르게 동작할 수 있으므로, SDK 호출 전 TripProof enable/env guard를 먼저 통과해야 한다.

## LangSmith 용어 기준

LangSmith 공식 문서는 trace를 한 operation의 runs 묶음으로 설명하고, run을 span에 해당하는 작업 단위로 설명한다. metadata와 tags는 trace/run을 필터링하거나 분류하는 보조 정보다.

이번 adapter는 runtime을 직접 감싸는 instrumentation이 아니라 완료된 export envelope를 후처리하는 sink다. 현재 `observation_export.v1` payload에는 step별 start/end time이나 duration이 없으므로, parent/leaf child runs는 실제 step latency가 아니라 observation record tree를 LangSmith UI tree로 펼친 synthetic runs다.

따라서 첫 adapter는 다음처럼 매핑한다.

```text
ObservationExportEnvelope
  -> LangSmith root run/span
      inputs: operation, subject
      outputs: final_status, failure_kind
      metadata: schema/version/record/runtime config/step status summary
      child runs: synthetic parent_step, leaf_step tree
      events: ordered parent_step, leaf_step entries
```

나중에 내부 record나 export payload가 step timing을 갖게 되면, selected parent/leaf child run에 실제 start/end/duration을 부여할 수 있다. 그 전에는 child run metadata에 `tripproof.synthetic_observation_step=true`를 남겨 latency 해석을 구분한다.

참고:

- LangSmith observability concepts: https://docs.langchain.com/langsmith/observability-concepts
- LangSmith custom instrumentation: https://docs.langchain.com/langsmith/annotate-code
- LangSmith metadata and tags: https://docs.langchain.com/langsmith/add-metadata-tags
- LangSmith input/output masking: https://docs.langchain.com/langsmith/mask-inputs-outputs

## Step mapping

root run에는 전체 step tree를 세 가지 방식으로 남긴다.

1. `metadata.step_statuses`: 모든 parent/leaf step의 status와 failure kind를 flat summary로 둔다.
2. child runs: export payload의 parent/leaf tree를 LangSmith trace tree로 펼친다.
3. `events`: export payload의 ordered tree를 순회해 parent/leaf step event를 순서대로 추가한다.

child run:

```text
run
  name
  run_type: chain
  inputs
    kind: parent_step | leaf_step
    name
    path
    parent_name
  outputs
    status
    failure_kind
    facts
  metadata
    tripproof.synthetic_observation_step: true
    tripproof.step.kind
    tripproof.step.name
    tripproof.step.path
    tripproof.step.status
    tripproof.step.failure_kind
    tripproof.step.facts
    tripproof.step.runtime_hints
    tripproof.runtime_hint.*
```

child run은 제품 실행 결과를 바꾸는 instrumentation이 아니라 완료된 export payload의 구조를 보기 좋게 투영한 것이다. 그래서 `not_started` step도 tree에 남길 수 있고, child run latency는 실제 step latency로 해석하지 않는다.

step facts는 child output과 metadata에 함께 둔다. LangSmith UI에서 step을 클릭했을 때 status/failure/facts를 바로 보기 위한 중복이며, source text나 answer body를 새로 추가하지 않는다.

parent step event:

```text
event
  kind: parent_step
  name
  path
  status
  failure_kind
  child_step_names
```

leaf step event:

```text
event
  kind: leaf_step
  name
  path
  parent_name
  status
  failure_kind
  facts
```

`not_started` step도 event로 남긴다. 이 adapter는 실제 elapsed time을 표현하지 않으므로, event와 child run은 "이 step이 실행됐다"가 아니라 "export payload에서 이 step이 이 상태였다"는 record entry다.

step timing은 다음 조건이 생길 때 다시 판단한다.

- export payload가 step별 start/end/duration을 가진다.
- product path의 실제 LangSmith instrumentation이 route/runtime 안에 들어간다.

## Runtime config metadata depth

`payload.runtime_config_snapshot`은 root run metadata에만 둔다.

```text
metadata
  tripproof.schema_version
  tripproof.operation
  tripproof.record_id
  tripproof.exported_at
  tripproof.final_status
  tripproof.failure_kind
  tripproof.subject
  tripproof.runtime_config_snapshot
  tripproof.step_statuses
```

검색과 grouping에 자주 쓰는 값은 root metadata에 flat key로 함께 둘 수 있다.

```text
tripproof.retrieval_backend
tripproof.retrieval_top_k
tripproof.embedding_provider
tripproof.embedding_model
tripproof.prompt_name
tripproof.prompt_version
tripproof.prompt_body_hash
tripproof.answer_model_backend
tripproof.answer_model
```

child event에는 full runtime config snapshot을 반복하지 않는다. leaf event는 해당 leaf의 `facts`만 가진다. `prompt_snapshot` leaf가 이미 prompt identity facts를 갖는 것은 유지할 수 있지만, adapter가 prompt body나 source text를 추가하지 않는다.

child run에는 full runtime config snapshot을 복사하지 않는다. 대신 해당 step을 이해하는 데 직접 필요한 runtime hint만 얇게 미러링한다.

| Step | Runtime hint |
| --- | --- |
| `retrieval_preparation`, `retrieval_repository_upsert` | retrieval backend/top-k/threshold |
| `embedding_record_build` | embedding auto-generate/provider/model/dimensions |
| `retrieval_pipeline`, `source_retrieval`, `context_assembly`, `candidate_summary` | retrieval backend/top-k/threshold |
| `source_retrieval` | embedding auto-generate/provider/model/dimensions |
| `prompt_snapshot` | prompt name/version/body hash |
| `composer_call` | answer model backend/model |
| `answer_pipeline` | prompt identity와 answer model summary |

부모 step에 필요한 hint는 부모 step에만, leaf step에 필요한 hint는 leaf step에만 둔다. 모든 runtime config를 모든 child run에 복사하지 않는다.

## Operation mapping details

### `material_upload`

root run:

```text
name: tripproof.material_upload
run_type: chain
inputs:
  operation: material_upload
  subject:
    material_id
outputs:
  final_status
  failure_kind
metadata:
  runtime_config_snapshot
  step_statuses
child runs:
  material_intake
    upload_snapshot
  content_extraction
    pdf_parse
  retrieval_preparation
    source_unit_build
    embedding_record_build
    retrieval_repository_upsert
  finalization
    material_status
events:
  material_intake
  upload_snapshot
  content_extraction
  pdf_parse
  retrieval_preparation
  source_unit_build
  embedding_record_build
  retrieval_repository_upsert
  finalization
  material_status
```

`upload_snapshot` event facts는 export projection이 이미 줄인 값만 쓴다. 원문 file name은 보내지 않고 `file_name_present`, `file_extension`, `content_type`, `size_bytes`, `size_limit_bytes` 같은 summary만 보낸다.

### `question_answer`

root run:

```text
name: tripproof.question_answer
run_type: chain
inputs:
  operation: question_answer
  subject: {}
outputs:
  final_status
  failure_kind
metadata:
  runtime_config_snapshot
  step_statuses
child runs:
  question_preparation
    query_snapshot
  material_scope
    ready_material_selection
    retrieval_record_load
  retrieval_pipeline
    source_retrieval
    context_assembly
    candidate_summary
  answer_pipeline
    prompt_snapshot
    composer_call
    answer_projection
  finalization
    question_status
events:
  question_preparation
  query_snapshot
  material_scope
  ready_material_selection
  retrieval_record_load
  retrieval_pipeline
  source_retrieval
  context_assembly
  candidate_summary
  answer_pipeline
  prompt_snapshot
  composer_call
  answer_projection
  finalization
  question_status
```

`query_snapshot` event facts는 `question_length`만 가진다. question text는 root inputs, event facts, metadata 어디에도 넣지 않는다.

`ready_material_selection`은 ready material id와 count까지만 남긴다. 요청 payload의 원문 material id 목록이나 failed/nonexistent id 진단은 export envelope에 없는 한 adapter가 새로 만들지 않는다.

`candidate_summary`는 count와 score presence summary만 남긴다. source unit text, candidate snippet, answer evidence snippet은 LangSmith에 기본으로 보내지 않는다.

`answer_projection`은 item count와 evidence state counts만 남긴다. answer body나 evidence body는 보내지 않는다.

## Default payload necessity boundary

LangSmith adapter의 기본 payload 기준은 민감정보 여부보다 필요성이다. 기본으로 보내는 값은 "실행을 다시 설명하는 데 필요한 진단 신호"여야 한다. 사용자 자료나 답변 내용을 재구성하기 위한 내용물은, 민감 여부와 무관하게 첫 adapter의 기본 payload에서 제외한다.

판단 질문:

- 이 값이 없으면 원인 범주를 못 나누는가?
- 같은 목적을 count, status, hash, id, presence summary로 대체할 수 있는가?
- LangSmith에서 봐야 하는가, local artifact나 product response에서 보면 충분한가?
- 이 값을 보낸 뒤에도 "내용 없이 실행 조건만 복원한다"는 설명이 유지되는가?

기본으로 보내는 값의 성격:

- operation, record id, final status, failure kind
- step name, path, status, failure kind
- source unit, embedding record, retrieval candidate, answer item 같은 count/status summary
- retrieval strategy, fallback 여부, vector candidate count
- runtime config의 retrieval, embedding, prompt identity, answer model summary
- answer projection의 item count와 evidence state counts

기본으로 보내지 않는 값의 성격:

- question text
- source unit text
- retrieval candidate text/snippet
- answer body
- evidence snippet/body
- raw PDF bytes
- parsed PDF text 전문
- provider raw request/response
- prompt body
- embedding vector
- exception stack
- API key, service role key, credential-bearing URL
- 원문 file name

이 경계는 LangSmith SDK의 hide inputs/outputs 설정보다 앞선다. SDK-level redaction은 보조 방어선일 수 있지만, TripProof adapter는 기본 payload를 만들 때부터 관찰 신호와 내용 재현용 값을 구분해야 한다.

## Env and no-op behavior

첫 구현의 activation contract는 TripProof 쪽 explicit gate를 둔다.

```text
TRIPPROOF_LANGSMITH_OBSERVATION_ENABLED=1
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=...
```

- `TRIPPROOF_LANGSMITH_OBSERVATION_ENABLED`가 truthy가 아니면 LangSmith sink만 비활성화된다.
- enable env가 있어도 `LANGSMITH_API_KEY`가 없으면 LangSmith sink만 비활성화된다. 이때 `TRIPPROOF_OBSERVATION_EXPORT_DIR`가 있으면 local artifact export는 계속 동작한다.
- `TRIPPROOF_OBSERVATION_EXPORT_DIR`와 LangSmith env가 모두 유효하면 같은 `ObservationExportEnvelope`를 local artifact와 LangSmith 양쪽에 fanout한다.
- `LANGSMITH_PROJECT`는 있으면 사용한다. 없을 때 SDK default project를 쓸지, TripProof default project를 둘지는 구현 시 작게 결정하되, API key가 없는 상태에서 startup이나 request를 실패시키지 않는다.
- LangSmith SDK import는 disabled 환경에서 startup failure를 만들면 안 된다. 가능하면 lazy import 또는 factory guard로 둔다.
- LangSmith client/run posting failure는 `ObservationExporter.export_observation()` 안에서 삼키고 product response를 바꾸지 않는다.
- Fanout에서는 한 sink가 실패해도 나머지 sink export를 계속 시도하고 product response를 바꾸지 않는다.

## 구현 결과

2026-06-11 현재 이 slice는 `apps/server/observations/langsmith.py`, app factory wiring, LangSmith exporter test로 구현됐다.

`LangSmithObservationExporter`는 `ObservationExporter` 구현체다. 입력은 `ObservationExportEnvelope` 하나이고, material/question 내부 record dataclass나 route recorder를 직접 import하지 않는다.

LangSmith mapping은 다음 구조로 닫았다.

```text
ObservationExportEnvelope
  -> langsmith_run_payload
      name: tripproof.material_upload | tripproof.question_answer
      run_type: chain
      inputs: operation, subject
      outputs: final_status, failure_kind
      metadata: schema/version/record/runtime config/step status summary
      child_runs: synthetic parent/leaf run tree
      events: ordered parent_step, leaf_step entries
  -> LangSmithRunWriter
```

실제 SDK 호출은 `LangSmithRunTreeWriter`가 담당한다. writer는 root `RunTree` 아래에 `create_child()`로 parent/leaf child runs를 만들고, root run에는 runtime config metadata를 붙인다. `langsmith.run_trees.RunTree`는 writer 안에서 lazy import하므로, LangSmith export가 비활성화된 환경에서 SDK import가 startup failure를 만들지 않는다.

app factory는 local artifact exporter와 LangSmith exporter를 독립적으로 모은다. `TRIPPROOF_OBSERVATION_EXPORT_DIR`가 있으면 local artifact exporter를 활성화하고, `TRIPPROOF_LANGSMITH_OBSERVATION_ENABLED`가 truthy이고 `LANGSMITH_API_KEY`가 있으면 LangSmith exporter를 활성화한다. 활성 exporter가 없으면 `NoopObservationExporter`, 하나면 해당 exporter, 둘 이상이면 `FanoutObservationExporter`를 사용한다.

`FanoutObservationExporter`는 같은 `ObservationExportEnvelope`를 등록된 exporter들에 순서대로 보낸다. 한 exporter가 실패해도 다음 exporter 호출을 계속하며, 실패를 product response로 전파하지 않는다.

테스트는 fake writer로 `material_upload`와 `question_answer` root run payload가 status/count/hash/config 중심으로 만들어지고, child run tree가 parent/leaf step 구조와 관련 runtime hint를 갖는지 확인한다. question text, source text, evidence snippet, answer body, 원문 file name이 들어가지 않는지와 writer failure를 주입해도 product response가 바뀌지 않는지도 확인한다. 또한 local artifact와 LangSmith가 함께 설정되면 fanout exporter가 선택되고, 한 sink 실패 후에도 다른 sink가 같은 envelope를 받는지 확인한다.

## 구현 slice

구현은 다음으로 제한한다.

- `LangSmithObservationExporter` 구현체를 추가한다.
- 입력은 `ObservationExportEnvelope` 하나다.
- 내부 material/question record, recorder, route orchestration은 건드리지 않는다.
- local artifact exporter와 같은 export envelope를 소비한다.
- LangSmith activation env가 없으면 LangSmith exporter를 선택하지 않는다.
- LangSmith 호출 실패가 product response를 바꾸지 않는 테스트를 추가한다.
- fake LangSmith client 또는 run writer로 mapping/redaction을 테스트한다.

권장 write scope:

- `apps/server/observations/export.py` 또는 `apps/server/observations/langsmith.py`
- `apps/server/core/config.py`
- `apps/server/app.py`
- `apps/server/tests/test_materials_api.py` 또는 새 observation exporter test file
- `.env.example`은 env 이름 설명이 필요할 때만 수정한다.
- `pyproject.toml`은 실제 SDK dependency를 추가하는 구현 slice에서만 수정한다.

건드리지 않을 scope:

- `apps/server/materials/observation.py`
- `apps/server/questions/observation.py`
- `apps/server/api/routes/materials.py`
- `apps/server/api/routes/questions.py`
- product API response schema
- local artifact JSONL payload schema

## 이번 AC

1. 06 spec은 LangSmith adapter가 내부 record가 아니라 `observation_export.v1` envelope만 소비한다고 정한다.
2. `material_upload`와 `question_answer`는 각각 LangSmith root run 하나로 매핑되고, root inputs/outputs는 safe summary만 가진다.
3. parent/leaf step은 synthetic child run tree, ordered events, root metadata step summary로 남긴다.
4. full runtime config snapshot은 root metadata depth에 두고, child run에는 해당 step을 해석하는 데 필요한 runtime hint만 선별해 둔다.
5. LangSmith 기본 payload는 실행 조건과 원인 범주를 설명하는 신호 중심으로 유지하고, 사용자 자료나 답변 내용을 재구성하기 위한 값은 기본 전송하지 않는다.
6. LangSmith env가 없거나 호출이 실패해도 product response는 no-op exporter와 동일해야 한다.
7. local artifact와 LangSmith가 모두 켜진 경우 같은 envelope가 양쪽 sink로 fanout되어야 한다.

## 확인 방법

1. LangSmith disabled 또는 API key missing 환경에서 app이 no-op exporter처럼 시작하고 material/question response가 기존과 동일한지 확인한다.
2. fake LangSmith client로 `material_upload` envelope export 시 root run name, inputs, outputs, metadata, child runs, events가 이 spec의 mapping을 따르는지 확인한다.
3. fake LangSmith client로 `question_answer` envelope export 시 question text, answer body, source text, evidence snippet 없이도 status/count/hash/config 중심 payload가 만들어지는지 확인한다.
4. fake LangSmith client failure를 주입해 material upload와 question answer public response가 바뀌지 않는지 확인한다.
5. 기존 local artifact exporter 테스트가 깨지지 않는지 확인한다.
6. local artifact와 LangSmith가 모두 설정된 환경에서 app factory가 fanout exporter를 선택하고, 한 sink 실패가 다른 sink export를 막지 않는지 확인한다.

현재 확인된 테스트:

- `uv run pytest apps/server/tests/test_materials_api.py -q`
- `uv run pytest apps/server/tests -q`

## 남은 판단

- LangSmith project default를 TripProof에서 정할지, SDK default에 맡길지.
- step timing이 생기면 어떤 parent/leaf step을 child span으로 승격할지.
- LangSmith trace id/run id를 product response나 local artifact에 연결할 필요가 있는가.

request/correlation id는 07 [Observation request/correlation id](07-observation-correlation-id.md)로 분리했다.

## 06 밖 후순위

- local artifact 파일 rotation/cleanup
- export artifact viewer
- eval run artifact 연결
