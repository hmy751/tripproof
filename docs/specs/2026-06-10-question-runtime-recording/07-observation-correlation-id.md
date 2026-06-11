# Observation request/correlation id

작성일: 2026-06-11

상태: 구현된 하위 작업 spec. `material_upload`와 `question_answer` export trace를 개별 요청과 사용자 흐름 기준으로 묶기 위한 request/correlation id 계약을 정한다.

## 왜 지금

01-06에서 내부 observation record, runtime config snapshot, local artifact export, LangSmith adapter, fanout exporter가 닫혔다. 이제 같은 `ObservationExportEnvelope`가 local JSONL과 LangSmith 양쪽에 남지만, 서로 다른 operation trace를 같은 사용자 흐름으로 묶는 공통 id는 없다.

특히 TripProof에서는 업로드 한 번 뒤 질문을 여러 번 할 수 있다. 이때 `material_id`는 같은 자료를 가리키는 id지만, 같은 브라우저 작업 흐름이나 대화 흐름을 뜻하지 않는다.

이 slice는 observation payload의 내용물을 늘리는 일이 아니라, 요청과 흐름을 찾기 위한 운반 메타를 붙이는 일이다.

## 사용자 장면

사용자가 PDF를 업로드하고 같은 화면에서 여러 질문을 이어서 한다.

```text
POST /api/materials
  -> material_id = mat_abc

POST /api/questions
  -> material_ids = [mat_abc]

POST /api/questions
  -> material_ids = [mat_abc]
```

개발자는 다음을 구분해서 볼 수 있어야 한다.

- 이 trace가 어느 HTTP 요청에서 생겼는가.
- 이 upload trace와 question trace가 같은 사용자 흐름에 속하는가.
- 이 question들이 같은 material을 대상으로 했는가.

## Goal

- `request_id`와 `correlation_id`를 둘 다 둔다.
- `request_id`는 HTTP 요청 하나를 식별한다.
- `correlation_id`는 업로드와 질문 여러 개를 묶는 사용자 흐름을 식별한다.
- `material_id`는 자료 단위 id이며 `correlation_id`를 대체하지 않는다.
- client는 `X-TripProof-Correlation-Id` request header로 correlation id를 전달할 수 있다.
- header가 없거나 쓸 수 없으면 server는 `correlation_id=request_id`로 fallback한다.
- `request_id`와 `correlation_id`는 `ObservationExportEnvelope` 최상위 필드에 둔다.
- product JSON body에는 기본 노출하지 않는다.
- 대신 response header로 `request_id`와 `correlation_id`를 노출한다.
- LangSmith와 local artifact는 같은 id 값을 소비한다.

## Rules

### ID 의미

`request_id`:

- 서버가 매 HTTP 요청마다 새로 생성한다.
- 같은 사용자 흐름 안에서도 요청마다 달라진다.
- client가 보낸 값을 그대로 request id로 신뢰하지 않는다.
- 형식은 opaque string이다. 첫 구현은 기존 repo id 관례와 맞춰 `req_` prefix와 짧은 random hex를 권장한다.

`correlation_id`:

- 여러 HTTP 요청을 같은 사용자 흐름으로 묶는 id다.
- client가 `X-TripProof-Correlation-Id`로 보내면 그 값을 사용한다.
- header가 없거나 빈 값이거나 유효하지 않으면 server-generated `request_id`를 fallback 값으로 사용한다.
- 같은 material을 대상으로 하는 모든 질문이 항상 같은 correlation id를 가져야 하는 것은 아니다. 자료 단위 연결은 `material_id`가 담당한다.

`material_id`:

- 자료 entity id다.
- 같은 자료를 대상으로 한 질문들을 찾는 데 유용하지만, 같은 사용자 흐름이나 같은 브라우저 세션을 의미하지 않는다.
- export payload의 `subject` 또는 step facts에 남을 수 있지만, request/correlation id의 대체물이 아니다.

### Header contract

Request header:

```text
X-TripProof-Correlation-Id: <opaque-flow-id>
```

- optional이다.
- 첫 구현은 ASCII alphanumeric과 `._:-` 문자만 허용하고, 길이는 1-128자로 제한한다.
- invalid header는 product 4xx를 만들지 않는다. server는 해당 값을 버리고 `request_id` fallback을 사용한다.
- correlation id는 secret이나 사용자 원문을 담는 곳이 아니다.

Response headers:

```text
X-TripProof-Request-Id: req_...
X-TripProof-Correlation-Id: corr_or_req_...
```

- 최소 적용 대상은 `POST /api/materials`와 `POST /api/questions`다.
- 구현이 middleware라면 모든 `/api/*` response에 붙어도 된다. 다만 07의 확인 기준은 observation export가 있는 material/question path다.
- error response에도 가능한 한 같은 header를 붙인다. 예를 들어 empty question, upload size limit 같은 product error에서도 요청 식별자는 남아야 한다.
- browser client가 header를 읽을 수 있도록 CORS expose header를 설정한다.

```text
Access-Control-Expose-Headers:
  X-TripProof-Request-Id,
  X-TripProof-Correlation-Id
```

JSON body:

- `Material` response body와 `QuestionResponse` body에는 `requestId`, `correlationId`를 추가하지 않는다.
- observability metadata를 product domain schema에 섞지 않는다.
- UI나 support workflow에서 body 노출이 필요해지면 별도 product decision으로 다룬다.

## Export envelope mapping

`ObservationExportEnvelope`에는 operation 공통 필드로 id를 둔다.

```json
{
  "schema_version": "tripproof.observation_export.v1",
  "exported_at": "2026-06-11T00:00:00Z",
  "operation": "question_answer",
  "record_id": "obs_question_...",
  "request_id": "req_...",
  "correlation_id": "flow_...",
  "payload": {}
}
```

- `request_id`와 `correlation_id`는 `payload` 안에 넣지 않는다.
- `payload.subject.material_id`와 `correlation_id`는 서로 다른 축이다.
- 기존 local artifact reader가 과거 JSONL을 읽을 수 있도록, consumer는 missing id를 허용해야 한다.
- schema version은 `tripproof.observation_export.v1`을 유지한다. 이번 변경은 additive top-level metadata로 본다.
- 구현 이후 새 export envelope는 두 id를 non-null string으로 채워야 한다.

## LangSmith mapping

LangSmith root run metadata:

```text
tripproof.request_id
tripproof.correlation_id
tripproof.correlation_id_source
```

- `tripproof.correlation_id_source`는 `header` 또는 `request_id_fallback`로 둔다.
- child run에는 기본적으로 request/correlation id를 반복하지 않는다. root run metadata가 trace 전체 식별을 담당한다.

LangSmith tags:

```text
tripproof.correlation:<correlation_id>
```

- correlation id는 UI에서 같은 사용자 흐름을 찾기 위한 tag로도 남긴다.
- `request_id`는 요청마다 고유하므로 tag로 남기지 않고 metadata에만 둔다.
- correlation tag가 너무 높은 cardinality로 운영상 불편해지면 tag 제거는 LangSmith adapter mapping 변경으로 처리할 수 있다. envelope 계약은 유지한다.

## Local artifact mapping

local JSONL은 envelope 최상위에 id를 그대로 쓴다.

```json
{
  "request_id": "req_...",
  "correlation_id": "flow_...",
  "payload": {}
}
```

local artifact 안에서 같은 사용자 흐름을 찾을 때는 `correlation_id`, 특정 요청을 찾을 때는 `request_id`, 같은 자료를 찾을 때는 `payload.subject.material_id` 또는 step facts의 material ids를 사용한다.

## 구현 방향

첫 구현은 request context를 만드는 얇은 server layer로 시작했다.

```text
HTTP request
  -> request/correlation context 생성
  -> route 처리
  -> internal observation record 생성
  -> ObservationExportEnvelope 생성 시 context attach
  -> response header attach
```

권장 write scope:

- `apps/server/app.py`: middleware 또는 equivalent request context wiring
- `apps/server/core/config.py`: CORS expose header 설정이 config에 있으면 함께 정리
- `apps/server/observations/export.py`: `ObservationExportEnvelope` top-level id 추가
- `apps/server/observations/langsmith.py`: metadata/tag mapping 추가
- `apps/server/tests/test_materials_api.py`: material/question response header, local export, LangSmith mapping 테스트

가능하면 내부 record에는 request/correlation id를 넣지 않는다.

- `MaterialUploadObservationRecord`와 `QuestionObservationRecord`는 product runtime fact를 소유한다.
- request/correlation id는 transport/export context다.
- route handler마다 id를 직접 전달하기보다 middleware/context provider 또는 dependency로 한 번에 묶는다.

## 구현 결과

- `apps/server/app.py`에서 HTTP middleware가 매 요청 `request_id`를 만들고, `X-TripProof-Correlation-Id`가 유효하면 `correlation_id`로 사용한다.
- header가 없거나 invalid이면 `correlation_id=request_id`로 fallback한다.
- response header에는 `X-TripProof-Request-Id`, `X-TripProof-Correlation-Id`를 붙인다.
- `apps/server/core/config.py`의 CORS expose header 설정으로 browser client가 두 response header를 읽을 수 있게 했다.
- `apps/server/observations/export.py`는 현재 request context를 `ObservationExportEnvelope` 최상위 `request_id`, `correlation_id`로 projection한다.
- local JSONL serialization은 `request_id`, `correlation_id`를 envelope top-level field로 남긴다.
- `apps/server/observations/langsmith.py`는 LangSmith root metadata에 `tripproof.request_id`, `tripproof.correlation_id`, `tripproof.correlation_id_source`를 넣고, tag에 `tripproof.correlation:<correlation_id>`를 남긴다.
- `apps/server/tests/test_materials_api.py`는 header fallback, invalid header fallback, local artifact, LangSmith metadata/tag, product JSON body 미노출, CORS expose header를 확인한다.

## Non-goals

- auth user id, session id, browser fingerprint를 만들지 않는다.
- `material_id`를 correlation id처럼 재해석하지 않는다.
- product JSON response schema를 바꾸지 않는다.
- LangSmith trace id/run id를 product response에 연결하지 않는다.
- eval run artifact와 correlation id 연결은 후속 작업으로 둔다.
- 프론트엔드가 어떤 시점에 새 correlation id를 생성할지까지 이번 spec에서 확정하지 않는다. 다만 server는 client-provided correlation id를 받을 수 있어야 한다.

## 이번 AC

1. 07 spec은 `request_id`, `correlation_id`, `material_id`의 의미와 경계를 구분한다.
2. server는 매 요청 `request_id`를 생성하고, `X-TripProof-Correlation-Id`가 없으면 `correlation_id=request_id`로 fallback한다.
3. `request_id`와 `correlation_id`는 `ObservationExportEnvelope` 최상위 필드로 export된다.
4. response JSON body에는 id를 추가하지 않고, response header로 `X-TripProof-Request-Id`, `X-TripProof-Correlation-Id`를 노출한다.
5. CORS는 browser client가 두 response header를 읽을 수 있게 expose한다.
6. LangSmith root metadata에는 두 id를 넣고, correlation id는 tag로도 남긴다.
7. missing 또는 invalid correlation header는 product response를 실패시키지 않는다.

## 확인 방법

1. `POST /api/materials`를 correlation header 없이 호출하면 response header에 `X-TripProof-Request-Id`와 같은 값의 `X-TripProof-Correlation-Id`가 있어야 한다.
2. `POST /api/questions`를 `X-TripProof-Correlation-Id: flow_test`로 호출하면 response header와 export envelope의 `correlation_id`가 `flow_test`여야 한다.
3. local artifact JSONL에는 `request_id`, `correlation_id`가 top-level field로 남아야 한다.
4. fake LangSmith writer는 root metadata의 `tripproof.request_id`, `tripproof.correlation_id`, correlation tag를 받아야 한다.
5. invalid correlation header를 보내도 material/question product status와 response body schema는 기존과 같아야 한다.
6. browser-origin request에서 response가 `X-TripProof-Request-Id`, `X-TripProof-Correlation-Id`를 expose해야 한다.

## 남은 판단

- 프론트엔드가 언제 새 correlation id를 생성하고 언제 기존 id를 이어 쓸지.
- eval run artifact가 `correlation_id`를 직접 소유할지, observation export envelope를 통해 연결할지.
- LangSmith correlation tag의 cardinality가 불편해지면 metadata-only로 줄일지.
- upstream proxy나 external gateway의 request id를 별도 필드로 받을 필요가 있는지.
