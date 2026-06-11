# 자료와 질문 실행 조건의 Runtime Observation Record

작성일: 2026-06-10

상태: 진행 중인 작업 spec. 01 prompt document runtime, 02 material upload observation, 03 question execution observation, 04 runtime config snapshot, 05 observation export boundary/local artifact exporter, 06 LangSmith observation adapter, 07 request/correlation id는 구현된 기준으로 정렬됐다.

## 왜 지금

TripProof는 사용자가 자료를 넣고 자료함에 질문해 근거가 붙은 답변을 받는 제품 경로를 갖기 시작했다. 다음 문제는 자료 업로드와 질문 답변이 흔들렸을 때 어떤 파일 처리 결과, prompt, provider, retrieval 설정, source 후보로 그 결과가 만들어졌는지 나중에 확인하기 어렵다는 점이다.

이번 작업은 LangSmith를 product 성공 기준으로 올리는 일이 아니다. `/api/materials`와 `/api/questions`의 product 응답 계약은 유지하고, 개발자가 같은 사용자 장면을 다시 확인할 때 실행 조건과 관찰 기록을 복원할 수 있게 한다.

관측 순서는 외부 trace provider보다 product runtime의 내부 record가 먼저다. material upload와 question answer의 parent/leaf observation record를 먼저 닫고, 그 다음 결과를 바꿀 수 있는 runtime config snapshot을 내부 record로 남긴다. LangSmith adapter는 그 record를 내보내는 출력 계층으로 붙인다.

## 사용자 장면

사용자가 여행 자료를 넣고 자료함에 묻는다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

자료가 `ready` 상태가 되고 답변이 `근거 있음`과 `근거 부족`을 함께 보여줄 때, 개발자는 다음을 확인할 수 있어야 한다.

- 어떤 material upload가 parse/source unit/embedding 생성까지 통과했는가.
- 어떤 active prompt가 답변 생성에 쓰였는가.
- 어떤 provider/model/retrieval 설정이 실행에 쓰였는가.
- 어떤 source unit 후보가 answer composer에 들어갔는가.
- 어떤 request와 사용자 흐름에서 material upload와 question answer trace가 생겼는가.
- 이 관찰 정보가 사용자-facing 자료 상태나 답변에 raw debug로 섞이지 않았는가.

## Goal

- active Library Chat prompt가 코드 본문 문자열이 아니라 이름, 버전, 본문 hash를 가진 prompt document로 분리된다.
- `/api/materials`와 `/api/questions` 경로에서 실행된 config와 prompt snapshot을 같은 원천에서 만들 수 있다.
- 내부 observation/snapshot record는 product 경로 옆에서 생성되며, product code가 eval run artifact나 fixture에 의존하지 않는다.
- LangSmith trace는 내부 record가 생긴 뒤 붙는 선택적 export adapter다.
- request/correlation id는 export envelope와 response header에서 요청/흐름을 식별하되 product JSON body에는 섞이지 않는다.
- 기본 material/question 응답 계약은 유지하고, raw retrieval/debug 정보는 사용자-facing 응답으로 노출하지 않는다.

## Rules

- `/api/materials`의 제품 흐름은 `upload -> parse -> source unit/embedding records -> ready/failed material -> 화면`이다. 내부 observation/snapshot record는 이 흐름을 관찰한다.
- `/api/questions`의 제품 흐름은 `ready material -> retrieval -> answer composer -> grounded ChatAnswer -> 화면`이다. 내부 observation/snapshot record는 이 흐름을 관찰한다.
- 내부 observation record가 먼저이고 LangSmith trace는 그 record를 외부로 내보내는 adapter다.
- prompt version/hash는 실행에 쓰인 prompt document에서 나온다. 기록용 값과 실행용 값이 따로 존재하면 안 된다.
- config snapshot은 provider/model/retrieval knob처럼 material/question 결과를 바꿀 수 있는 값만 먼저 담는다.
- LangSmith export가 비활성화되어도 material upload와 question answer의 응답 계약은 동일하게 동작해야 한다.
- request/correlation id는 observation transport metadata다. response header로는 노출하되 product JSON body에는 넣지 않는다.
- eval runner나 run artifact는 product code가 import하지 않는다. eval은 product entry point를 호출하고 결과를 기록한다.
- source unit 후보나 LLM raw payload를 기본 API 응답에 붙여 product answer처럼 만들지 않는다.

## Non-goals

- LangSmith trace를 product 통과 기준이나 배포 gate로 쓰지 않는다.
- metric threshold, dashboard, pass/fail gate를 확정하지 않는다.
- 모든 endpoint에 관측 레이어를 붙이지 않는다. 먼저 `POST /api/materials`와 `POST /api/questions`만 본다.
- prompt admin UI나 DB 기반 prompt registry는 이번 범위가 아니다.
- raw LLM payload 저장, 장기 로그 보관, 개인정보 마스킹 정책 전체는 이번 범위가 아니다.

## 하위 spec

| 순서 | 문서 | 역할 |
| --- | --- | --- |
| 01 | [Prompt document runtime과 Library Chat renderer](01-prompt-document-runtime.md) | Library Chat prompt를 versioned markdown document로 분리하고, 공통 runtime과 answer renderer의 책임 경계를 정한다 |
| 02 | [Material upload 관측 record](02-material-upload-observation.md) | `POST /api/materials`의 upload, parse, source unit/embedding record 생성, retrieval repository upsert, ready/failed 경계를 내부 observation record로 남기는 기준을 정한다 |
| 03 | [Question execution 관측 record](03-question-observation.md) | `POST /api/questions`의 ready material 선택, retrieval 실행, answer composer 호출, accepted/blocked 경계를 내부 observation record로 남기는 기준을 정한다 |
| 04 | [Runtime config snapshot](04-runtime-config-snapshot.md) | material/question 결과를 바꿀 수 있는 retrieval, embedding, prompt, provider/model knob을 내부 snapshot으로 남기는 기준을 정한다 |
| 05 | [Observation export boundary](05-observation-export-boundary.md) | 내부 observation record와 runtime config snapshot을 no-op, local artifact, LangSmith 같은 export sink로 내보내는 계약을 정한다 |
| 06 | [LangSmith observation adapter](06-langsmith-observation-adapter.md) | `observation_export.v1` payload를 LangSmith root run, synthetic child run tree, events, metadata로 매핑하는 계약을 정한다 |
| 07 | [Observation request/correlation id](07-observation-correlation-id.md) | request 단위와 사용자 흐름 단위를 구분해 local artifact, LangSmith, response header에서 같은 trace를 찾는 계약을 정한다 |

## 현재 코드에서 볼 곳

- `apps/server/api/routes/materials.py`: `/api/materials`가 upload, PDF parse, ready/failed material 생성을 연결한다.
- `apps/server/api/routes/questions.py`: `/api/questions`가 ready material, retrieval, `ChatAnswer`를 연결한다.
- `apps/server/app.py`: app factory, CORS, request/correlation context, observation exporter wiring의 경계다.
- `apps/server/materials/store.py`: ready material에서 source unit과 embedding record를 만든다.
- `apps/server/materials/observation.py`: material upload parent/leaf observation record를 정의한다.
- `apps/server/questions/observation.py`: question answer parent/leaf observation record와 prompt snapshot safe facts를 정의한다.
- `apps/server/observations/export.py`: material/question observation record를 request/correlation id가 붙은 `observation_export.v1` payload로 projection하고 no-op/local artifact exporter를 제공한다.
- `apps/server/observations/langsmith.py`: `observation_export.v1` payload를 LangSmith root run, child run, metadata, correlation tag로 projection한다.
- `apps/server/retrieval/search.py`: retrieval top-k, similarity threshold, source retrieval strategy 경계다.
- `apps/server/answers/library_chat.py`: Library Chat answer composer가 prompt renderer를 사용한다.
- `apps/server/prompts/README.md`: prompt document/runtime/renderer 책임 경계를 설명한다.
- `apps/server/prompts/assets/answer/library_chat_answer/2026-06-10.md`: 현재 active Library Chat prompt document다.
- `apps/server/prompts/runtime/prompt_document.py`: prompt markdown의 metadata, body, hash를 읽는 공통 runtime이다.
- `apps/server/prompts/runtime/prompt_store.py`: `assets/{domain}/{name}/{version}.md` 경로를 해석한다.
- `apps/server/prompts/renderers/answer/library_chat_answer.py`: Library Chat prompt body를 provider 입력으로 렌더한다.
- `apps/server/core/config.py`: provider, embedding, retrieval 설정의 현재 원천이다.
- `apps/server/runtime/config_snapshot.py`: material/question observation record에 붙는 runtime config snapshot을 정의한다.
- `apps/server/llm/ollama.py`: provider call 경계다.
- `eval/README.md`, `eval/runs/README.md`: eval은 product behavior 관찰자라는 기록 경계다.

## 구현면 펼치기

| 구현 요소 | 이번 장면에서 필요한 이유 | 현재 코드/문서 비교 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Material ingest observation | 질문 결과가 어떤 material 처리 결과에서 나왔는지 추적해야 한다 | `/api/materials`는 parent/leaf step 기반 내부 observation record를 남긴다 | material upload, parse success/failure, source unit/embedding record 생성, ready/failed 경계를 내부 record로 남긴다 |
| Runtime config snapshot | provider/model/retrieval knob이 자료 처리와 답변을 바꾼다 | `core/config.py`에 flat env constants가 있고 app/store/retrieval/composer가 각각 소비한다 | material/question 실행에 영향을 주는 값만 snapshot으로 만든다 |
| Prompt snapshot | prompt 변경과 답변 변경을 연결해야 한다 | question observation record가 composer에서 노출한 prompt identity를 safe facts로 남긴다 | prompt domain/name/version/body hash를 실행 기록에 연결한다 |
| Question path observation | 답변 흔들림을 retrieval/compose 경계에서 봐야 한다 | `/api/questions`는 parent/leaf step 기반 내부 observation record를 남기고 public response는 유지한다 | 내부 관찰 record는 만들되 기본 response에는 raw debug를 섞지 않는다 |
| Observation export boundary | 내부 record를 no-op/local/LangSmith로 내보내는 운반 경로가 필요하다 | 05에서 export envelope/projection/sink 책임을 작성하고 no-op/local artifact exporter를 구현했다 | 내부 record shape를 흔들지 않는 JSON-safe export payload와 no-op/local/LangSmith 책임을 닫는다 |
| LangSmith export | 로컬 record만으로는 요청 단위 tree를 외부 관측 도구에서 함께 보기 어렵다 | 06에서 `observation_export.v1` payload를 LangSmith root run, synthetic child run tree, step event로 내보내는 adapter를 구현했다 | 내부 observation/snapshot export payload를 LangSmith로 내보내고, 꺼진 환경에서는 no-op로 통과한다 |
| Observation correlation id | upload trace와 question trace가 같은 사용자 흐름인지 묶어야 한다 | 07에서 request/correlation id 계약을 작성했고 `apps/server/app.py`, `apps/server/observations/export.py`, `apps/server/observations/langsmith.py`에 구현했다 | `ObservationExportEnvelope`와 response header에 request/correlation id를 연결하되 product JSON body는 유지한다 |
| Eval run record | 제품 동작을 반복 관찰해야 한다 | `eval/runs`는 placeholder 원칙만 있다 | product entry point, config snapshot, observed answer, failure, next verification point를 남길 수 있게 한다 |

## 현재 slice 순서

01 [Prompt document runtime과 Library Chat renderer](01-prompt-document-runtime.md)는 구현됐다. Library Chat prompt는 versioned markdown document로 로드되고, answer composer는 renderer를 통해 provider 입력을 만든다.

02 [Material upload 관측 record](02-material-upload-observation.md)는 구현됐다. 02 구현 당시에는 LangSmith adapter를 붙이지 않고 `material_upload` parent/leaf step 기록까지만 닫았다.

03 [Question execution 관측 record](03-question-observation.md)는 구현됐다. 현재 구현은 `question_answer`를 parent/leaf step으로 남기고, prompt snapshot은 composer가 노출하는 prompt identity를 safe facts로 기록한다.

04 [Runtime config snapshot](04-runtime-config-snapshot.md)는 구현됐다. material/question 결과를 바꿀 수 있는 retrieval backend, retrieval limit/threshold, embedding auto-generate, embedding provider/model/dimensions, prompt snapshot 연결, answer model backend/model 자리를 내부 snapshot으로 남긴다.

05 [Observation export boundary](05-observation-export-boundary.md)는 구현됐다. 내부 record와 runtime config snapshot을 `observation_export.v1` payload로 projection하고, no-op/local artifact/LangSmith의 책임을 분리한다. local artifact exporter는 configured directory에 JSONL로 append하며, 원문 파일명은 extension/presence summary로 줄인다.

06 [LangSmith observation adapter](06-langsmith-observation-adapter.md)는 구현됐다. LangSmith adapter는 내부 record와 runtime config snapshot이 export payload로 닫힌 뒤 optional sink로 연결하며, 첫 mapping은 operation root run, synthetic parent/leaf child runs, step events를 기준으로 한다. Synthetic child runs는 observation tree를 LangSmith UI에 투영한 표현이며, 현재 step별 실제 latency나 duration을 의미하지 않는다. local artifact와 LangSmith가 모두 설정되면 같은 export envelope를 fanout으로 양쪽에 보낸다.

07 [Observation request/correlation id](07-observation-correlation-id.md)는 구현됐다. `request_id`는 HTTP 요청 단위, `correlation_id`는 사용자 흐름 단위로 구분하고, `material_id`는 자료 단위 id로 남긴다. product JSON body에는 id를 넣지 않고, response header와 export envelope, LangSmith metadata/tag로 연결한다. header가 없거나 invalid이면 `correlation_id=request_id`로 fallback한다.

이 slice는 product answer를 바꾸는 작업이 아니라, 같은 product result가 어떤 조건에서 만들어졌는지 복원 가능하게 만드는 작업이다. 자료 상태나 답변이 바뀌면 그 변화는 material parsing/source unit 생성 때문인지, prompt/config 변경 때문인지, retrieval 후보 변경 때문인지 관찰할 수 있어야 한다.

## 이번 AC

1. `POST /api/materials`는 upload, parse, source unit/embedding record 생성, ready/failed 경계를 내부 observation record로 남길 수 있다.
2. active Library Chat prompt는 이름과 버전을 가진 document에서 로드되고, answer composer는 그 document를 사용한다.
3. `POST /api/questions`는 ready material 선택, retrieval, context assembly, prompt snapshot, composer call, answer projection, accepted/blocked 경계를 내부 observation record로 남길 수 있다.
4. material/question 실행에서 결과를 바꿀 수 있는 provider/model/retrieval/prompt 관련 runtime config snapshot을 만들 수 있어야 한다.
5. export boundary는 내부 observation/snapshot record를 JSON-safe payload로 projection하고, no-op/local artifact/LangSmith sink가 꺼져 있거나 실패해도 기존 material/question 응답 계약을 유지한다.
6. request/correlation id는 export envelope와 response header에서 요청/흐름을 식별하되 product JSON body에는 섞이지 않아야 한다.
7. 첫 client 연결은 App mount/browser tab 단위 correlation id를 만들고, upload/question 요청에 같은 `X-TripProof-Correlation-Id` header를 보낸다.

## 확인 방법

1. 기존 숙소 체크인 자료 장면에서 `/api/materials`로 PDF를 업로드한다.
2. 자료가 기존처럼 ready/failed material 응답 계약을 지키는지 확인한다.
3. `/api/questions`를 호출해 답변의 `근거 있음`/`근거 부족` 동작이 기존 기준과 동일한지 확인한다.
4. material/question 실행의 내부 observation/snapshot record가 raw payload 없이 만들어지는지 확인한다.
5. runtime config snapshot이 material/question 내부 record와 연결되고, 응답 payload에는 노출되지 않는지 확인한다.
6. local artifact exporter가 붙는 이후 export slice에서는 내부 record가 JSON-safe payload로 projection되고 raw/source/provider/secret 값이 없는지 확인한다.
7. LangSmith adapter에서는 같은 export payload가 material/question root run, synthetic child run tree, event로 export되는지 확인한다.
8. export sink가 비활성화되거나 실패한 환경에서도 기존 product path가 유지되는지는 export slice의 확인 항목으로 둔다.
9. 응답 payload가 raw retrieval candidate, raw LLM JSON, eval score를 사용자-facing answer처럼 포함하지 않는지 확인한다.
10. 07 구현에서는 request/correlation id가 response header, export envelope, LangSmith metadata/tag에 연결되고 JSON body에는 들어가지 않는지 확인한다.

## 남은 판단

- 새 material batch, explicit session reset, route 전환 같은 product 경계가 생기면 App mount/browser tab 단위 correlation id를 더 좁힐지.
- eval run artifact가 `correlation_id`를 직접 소유할지, observation export envelope를 통해 연결할지.
- LangSmith correlation tag의 cardinality가 불편해지면 metadata-only로 줄일지.
- step timing이 생기면 synthetic child run을 실제 duration이 있는 span으로 어떻게 승격할지.
- local artifact 파일 rotation/cleanup과 artifact viewer를 언제 붙일지.
