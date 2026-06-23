# Observation export boundary

작성일: 2026-06-11

상태: 구현된 하위 작업 spec. 내부 material/question observation record와 runtime config snapshot을 no-op, local observation artifact, LangSmith 같은 export sink로 내보내는 계약을 정한다. local observation artifact exporter와 LangSmith adapter는 구현된 기준으로 정렬됐다.

## 왜 지금

01-04에서 active prompt document, material upload observation, question execution observation, runtime config snapshot이 내부 record로 닫혔다. 이제 남은 문제는 이 record를 어디로 내보내고, 어떤 형태로 검토할지다.

LangSmith를 바로 붙이면 외부 trace provider가 record shape를 끌고 갈 수 있다. 반대로 기존 material/question observation sink를 무작정 확장하면 product path의 내부 관측 계약과 export 운반 경로가 섞일 수 있다.

이 slice는 내부 record를 바꾸는 작업이 아니라, 내부 record를 소비하는 export boundary를 잡는 작업이다. 먼저 local observation artifact exporter로 파일에 떨어지는 JSON-safe payload를 확인하고, 그 다음 같은 payload를 LangSmith trace/span/metadata로 매핑한다.

## 사용자 장면

사용자가 PDF 자료를 업로드하고 자료함에 질문한다. API 응답은 기존처럼 material과 question response만 반환한다.

개발자는 API 응답에 debug field를 추가하지 않고도, 요청 뒤에 남은 local observation artifact나 이후 LangSmith trace에서 다음을 확인할 수 있어야 한다.

- material upload record가 어떤 operation, final status, failure kind, safe step facts를 가졌는가.
- question answer record가 어떤 material scope, retrieval summary, prompt snapshot, final status를 가졌는가.
- runtime config snapshot이 record와 함께 export됐는가.
- export payload가 SourceUnit text, answer body, raw provider payload, embedding vector, secret을 포함하지 않는가.
- export sink가 꺼져 있거나 실패해도 product response가 그대로 유지되는가.

## Goal

- 내부 `MaterialUploadObservationRecord`와 `QuestionObservationRecord`는 product-owned observation contract로 유지한다.
- export 계층은 내부 record를 직접 소유하지 않고 JSON-safe export payload로 projection해 소비한다.
- no-op, local observation artifact, LangSmith의 책임을 분리한다.
- 첫 구현은 local observation artifact exporter로 시작해 payload shape와 projection boundary를 파일로 검증할 수 있게 한다.
- LangSmith adapter는 같은 export payload를 trace/span/metadata로 매핑하는 선택적 sink로 둔다.
- export payload는 product API 응답, material status, question status, exception propagation을 바꾸지 않는다.

## Rules

- 내부 record shape의 소유자는 exporter가 아니라 `/api/materials`와 `/api/questions` product runtime이다.
- 기존 operation-specific observation sink는 내부 emission boundary로 유지한다. 공통 exporter는 그 아래에서 record를 export payload로 projection하는 운반 계층이다.
- export payload는 dataclass object를 그대로 직렬화한 덤프가 아니라 versioned envelope다.
- export envelope는 operation, record id, export schema version, exported-at timestamp, projected payload를 가진다.
- request/correlation id 계약이 추가된 뒤 export envelope는 request id, correlation id, correlation id source도 top-level metadata로 가진다. local artifact, LangSmith, future sink는 이 세 값을 같은 의미로 보존해야 한다.
- projection은 내부 record의 step name, status, failure kind, allowlisted facts, runtime config snapshot summary를 보존하되 raw/source/provider/secret 값을 추가하지 않는다.
- export projection은 내부 record보다 더 엄격할 수 있다. 예를 들어 내부 material record의 `file_name`은 외부 export payload에서는 기본적으로 원문 파일명 대신 파일명 존재 여부나 extension summary로 줄인다.
- local observation artifact exporter는 configured directory에 JSONL 같은 append-friendly 파일로 기록한다. 기본 product path는 no-op이어야 하며, repo-local 출력 경로를 쓰는 구현에서는 해당 경로를 git ignore 대상에 둔다.
- LangSmith adapter는 export payload를 소비해 trace/run/span/metadata로 매핑한다. LangSmith trace shape가 내부 record나 export payload schema를 다시 결정하면 안 된다.
- exporter가 예외를 내도 material upload, question answer, material store 상태, public response contract, existing exception propagation을 바꾸지 않는다.

## Non-goals

- LangSmith SDK dependency, project name, run/span mapping을 이번 spec 작성에서 확정하지 않는다.
- observation record 저장소의 장기 보관, 검색 UI, retention policy를 만들지 않는다.
- raw PDF, SourceUnit text, retrieval 후보(RetrievedSource) 전문, answer body 전문, provider raw response, embedding vector, secret을 저장하지 않는다.
- API 응답에 `observation`, `runtimeConfig`, `debug`, `traceId`, `exportPath` 같은 필드를 추가하지 않는다.
- eval runner나 eval run artifact를 product code가 import하게 만들지 않는다.
- 모든 endpoint의 observability를 일반화하지 않는다. 먼저 `material_upload`와 `question_answer`만 다룬다.

## 현재 코드에서 볼 곳

- `apps/server/materials/observation.py`: material upload record, operation-specific sink, 테스트용 in-memory sink, emit helper를 정의한다.
- `apps/server/questions/observation.py`: question answer record, operation-specific sink, 테스트용 in-memory sink, emit helper를 정의한다.
- `apps/server/observations/export.py`: 기존 import 경로를 보존하는 compatibility re-export 경계다.
- `apps/server/observations/envelope.py`: 공통 export envelope와 operation type을 정의한다.
- `apps/server/observations/serializers.py`: material/question record를 export-safe envelope로 projection한다.
- `apps/server/observations/redaction.py`: export-safe fact와 file name summary projection을 정의한다.
- `apps/server/observations/sinks.py`: no-op/local/fanout exporter와 operation-specific bridge sink를 정의한다.
- `apps/server/runtime/config_snapshot.py`: record에 embed되는 runtime config snapshot을 정의한다.
- `apps/server/api/routes/materials.py`: material upload observation recorder를 만들고 sink에 emit한다.
- `apps/server/api/routes/questions.py`: question observation recorder를 만들고 sink에 emit한다.
- `apps/server/app.py`: 기본 export observation sink(미설정 시 no-op exporter)를 app state에 연결한다.
- `apps/server/core/config.py`: `TRIPPROOF_OBSERVATION_EXPORT_DIR` 설정을 읽는다.
- `apps/server/tests/test_materials_api.py`: internal record와 sink failure non-blocking behavior를 확인한다.
- `docs/implementation-notes/2026-06-11-observation-record-trace-boundary/index.md`: 내부 record와 external trace provider의 역할 경계를 설명한다.

## 구현면 펼치기

| 구현 요소 | 필요한 이유 | 현재 코드/문서 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Export envelope | sink별 format이 record shape를 흔들지 않게 해야 한다 | 아직 공통 export payload가 없다 | `schema_version`, `operation`, `record_id`, `exported_at`, projected payload를 가진 JSON-safe envelope가 있다 |
| Record projection | 내부 record object를 그대로 외부로 흘리면 export payload가 내부 record shape에 묶인다 | internal record는 safe facts allowlist를 갖지만 export 전용 projection 규칙은 없다 | material/question record를 export-safe dict로 변환하고, file name 같은 field는 external summary로 줄인다 |
| Common export sink | no-op/local/LangSmith를 같은 운반 계약 아래 둬야 한다 | material/question sink가 operation별로 분리돼 있다 | `export_observation(payload)` 형태의 공통 sink 또는 동등한 protocol이 있다 |
| Operation-specific bridge | 기존 product path를 크게 흔들지 않고 exporter를 붙여야 한다 | `MaterialUploadObservationExportSink`, `QuestionObservationExportSink`가 record를 projection해 common exporter에 넘긴다 | material/question observation sink implementation이 record를 projection해 common exporter에 넘긴다 |
| No-op exporter | export가 꺼진 환경에서도 product path가 동일해야 한다 | `NoopObservationExporter`가 기본 export disabled 동작을 담당한다 | export disabled 기본값이 no-op이고 응답/예외 동작이 바뀌지 않는다 |
| Local observation artifact exporter | LangSmith 전에 payload shape와 projection을 눈으로 확인해야 한다 | `LocalArtifactObservationExporter`가 configured directory에 JSONL로 append한다 | configured directory에 observation/export JSONL artifact를 남기고, raw/source/provider/secret이 없는지 테스트로 확인한다 |
| LangSmith adapter | 외부 trace provider는 내부 record를 소비하는 선택 계층이어야 한다 | dependency와 adapter가 없다 | 후속 작업에서 export payload를 trace/span/metadata로 매핑하되 product path는 no-op와 동일하게 유지한다 |

## Export payload v1

첫 export payload는 내부 record의 의미를 옮기되, 내부 dataclass 구조를 외부 sink 계약으로 고정하지 않는다.

```text
observation_export
  schema_version: tripproof.observation_export.v1
  exported_at
  operation: material_upload | question_answer
  record_id
  payload
    final_status
    failure_kind
    subject
    steps
    runtime_config_snapshot
```

`payload.steps`는 parent/leaf tree를 유지한다.

```text
step
  name
  status
  failure_kind
  facts
  children
```

`subject`는 operation별 최소 식별자만 담는다.

| Operation | subject |
| --- | --- |
| `material_upload` | `material_id` |
| `question_answer` | 비워 둘 수 있음. 이후 request id가 생기면 추가한다 |

`final_status`는 operation별 final status를 같은 위치로 올린다.

| Operation | 내부 field | export field |
| --- | --- | --- |
| `material_upload` | `final_material_status` | `final_status` |
| `question_answer` | `final_question_status` | `final_status` |

runtime config snapshot은 이미 secret/raw 값을 갖지 않는 safe snapshot이므로 export payload에 포함할 수 있다. 다만 prompt body, SourceUnit text, vector, provider raw response, secret 값을 새로 채워 넣지 않는다.

## Projection rules

내부 record의 allowlist는 export projection의 최소 기준이다. export projection은 sink로 나가는 경계이므로 더 엄격하게 줄일 수 있다.

공통 projection에서 유지한다.

- operation
- record id
- final status
- failure kind
- step name/status/failure kind
- step별 safe facts 중 export-safe value
- runtime config snapshot의 retrieval, embedding, prompt identity, answer model summary

공통 projection에서 넣지 않는다.

- raw PDF bytes
- parsed text 전문
- SourceUnit text
- retrieval 후보(RetrievedSource) 전문
- answer body 전문
- provider raw request/response
- exception stack
- embedding vector
- secret, API key, service role key, URL credential

처음부터 줄여서 내보낸다.

| 내부 fact | export payload |
| --- | --- |
| `file_name` | 원문 파일명 대신 `file_name_present`, `file_extension` 같은 summary |
| `content_type` | 유지 |
| `size_bytes`, `size_limit_bytes` | 유지 |
| `ready_material_ids` | 유지. 사용자 입력 payload의 requested id 목록은 추가하지 않음 |
| `prompt_asset_path` | repo-relative path만 유지. 외부 provider policy가 더 엄격해지면 LangSmith adapter에서 omit 가능 |

## Sink responsibilities

### No-op

- 기본값이다.
- export payload를 만들지 않거나, 만들어도 버린다.
- 설정 없이 product path가 기존처럼 동작해야 한다.

### Local observation artifact

- 첫 구현 대상이다.
- configured directory에 JSONL로 append한다.
- 파일 쓰기 실패는 product response를 바꾸지 않는다.
- local observation artifact는 product source of truth가 아니며, API 응답이나 material/question 상태에서 참조하지 않는다.
- repo-local directory를 쓰면 git ignore 대상이어야 한다.

### LangSmith adapter

- 후속 구현 대상이다.
- export payload를 LangSmith trace/run/span/metadata로 projection한다.
- LangSmith가 꺼졌거나 SDK 설정이 없으면 no-op와 같은 product behavior를 가진다.
- LangSmith input/output field에 question text, answer text, SourceUnit text, raw provider payload를 기본으로 넣지 않는다.
- LangSmith-specific run id나 trace id가 생기더라도 API 응답에 노출하지 않는다.

## 구현 결과

2026-06-11 최초 구현은 `apps/server/observations/export.py`, app factory wiring, local observation artifact test로 닫혔다. 2026-06-15 server boundary refactor 이후 export envelope, serializer, export-safe projection, sink 책임은 `apps/server/observations/` 하위 module로 분리됐다.

공통 export envelope는 다음 top-level field를 가진다.

```text
schema_version
exported_at
operation
record_id
request_id
correlation_id
correlation_id_source
payload
```

`MaterialUploadObservationExportSink`와 `QuestionObservationExportSink`는 기존 operation-specific sink interface를 구현하고, 내부 record를 `observation_export.v1` payload로 projection해 공통 exporter에 넘긴다. app factory는 별도 sink가 주입되지 않은 경우 이 bridge sink를 기본으로 사용한다.

2026-06-15 server boundary refactor 이후 local JSONL serialization과 LangSmith adapter는 같은 `ObservationExportEnvelope`의 `request_id`, `correlation_id`, `correlation_id_source`를 소비한다. 특정 sink에만 이 값이 남거나 빠지는 상태는 export 계약 drift로 본다.

`TRIPPROOF_OBSERVATION_EXPORT_DIR`이 비어 있으면 `NoopObservationExporter`가 사용된다. 값이 있으면 `LocalArtifactObservationExporter`가 해당 directory의 `observation-export.jsonl`에 append한다. `.env.example`에는 repo-local 확인용 예시 directory를 주석으로 남겼고, 해당 directory는 `.gitignore`에 추가했다.

local observation artifact projection은 내부 record의 step tree와 runtime config snapshot을 유지하되, `upload_snapshot.file_name`은 원문 파일명 대신 `file_name_present`, `file_extension` summary로 줄인다. 테스트는 export JSONL에 question text, answer body, SourceUnit text, 원문 file name이 없는지 확인한다.

## 이번 AC

1. `05-observation-export-boundary`는 internal material/question observation record와 external export sink의 책임을 분리한다.
2. export payload v1은 operation, record id, final status, failure kind, steps, runtime config snapshot을 JSON-safe projection으로 담고, 내부 record dataclass를 그대로 외부 계약으로 삼지 않는다.
3. no-op, local observation artifact, LangSmith adapter의 책임과 실패 동작이 구분된다.
4. local observation artifact exporter가 첫 구현 대상이며, LangSmith adapter는 같은 payload를 소비하는 후속 optional sink로 남는다.
5. export payload에는 raw/source/provider/secret 값이 들어가지 않고, file name처럼 내부에는 남아 있는 field도 외부 export에서는 summary로 줄인다.
6. export sink가 비활성화되거나 실패해도 material/question public response와 exception propagation은 동일해야 한다.

## 확인 방법

1. `uv run pytest apps/server/tests/test_materials_api.py`
2. `uv run pytest apps/server/tests`
3. export disabled 상태에서 material upload와 question response payload가 기존과 동일한지 확인한다.
4. local observation artifact exporter를 temp directory로 설정하고 material/question 요청 후 JSONL payload가 생성되는지 확인한다.
5. local observation artifact payload에 `observation_export.v1`, operation, record id, final status, steps, runtime config snapshot이 있는지 확인한다.
6. local observation artifact payload에 question text, answer body, SourceUnit text, raw provider payload, embedding vector, secret, 원문 file name이 없는지 확인한다.
7. local observation artifact 쓰기 실패를 주입해도 public response와 기존 exception propagation이 바뀌지 않는지 확인한다.

현재 확인된 테스트:

- `uv run pytest apps/server/tests/test_materials_api.py`
- `uv run pytest apps/server/tests`

## 남은 판단

- operation-specific sink에서 exporter로 바로 보내는 구조는 유지하고, local observation artifact와 LangSmith 동시 전송은 06 보강의 `FanoutObservationExporter`로 닫았다.
- local observation artifact 파일을 operation별로 나눌지, 하나의 JSONL stream으로 둘지.
- LangSmith에서 parent step을 span으로 둘지, leaf step만 event/metadata로 둘지.
- `exported_at`만 둘지, 내부 record 생성 시각도 record 자체에 추가할지.

request/correlation id는 07 [Observation request/correlation id](07-observation-correlation-id.md)에서 export envelope top-level metadata로 연결했다.
