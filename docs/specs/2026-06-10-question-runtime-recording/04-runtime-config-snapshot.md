# Runtime config snapshot

작성일: 2026-06-11

상태: 구현된 하위 작업 spec. material upload와 question answer 결과를 바꿀 수 있는 runtime knob을 내부 snapshot으로 남기는 기준을 정한다.

## 왜 지금

01은 active Library Chat prompt를 document identity로 분리했고, 02와 03은 material/question product path의 실행 fact를 parent/leaf observation record로 남긴다. 이제 같은 자료와 질문 결과가 흔들렸을 때 어떤 retrieval backend, retrieval limit/threshold, embedding 설정, prompt identity, provider/model 조건에서 만들어졌는지 확인할 수 있어야 한다.

지금은 observation sink/export boundary보다 runtime config snapshot이 먼저다. snapshot은 "무엇이 결과를 바꿨는가"라는 내용물이고, sink/export는 그 기록을 LangSmith나 local observation artifact로 보내는 운반 경로다. 내용물이 덜 닫힌 상태에서 export부터 붙이면 exporter shape가 관측 모델을 끌고 갈 수 있다.

## 사용자 장면

사용자가 PDF 자료를 업로드하고 자료함에 질문한다. public API 응답은 기존처럼 material과 question response만 반환한다. 개발자는 내부 record를 통해 다음을 확인할 수 있어야 한다.

- material upload가 어떤 retrieval backend와 embedding 생성 조건에서 source unit/embedding record를 만들었는가.
- question answer가 어떤 retrieval limit/threshold와 backend 조건에서 retrieval 후보(RetrievedSource)를 골랐는가.
- answer composer가 어떤 prompt identity와 연결됐는가.
- 현재 answer composer backend/model 또는 이후 LLM provider/model이 명시될 때 그 자리를 같은 snapshot 계약 안에 둘 수 있는가.

## Goal

- material upload와 question answer에 연결할 수 있는 내부 runtime config snapshot을 만든다.
- snapshot은 result-changing knob만 담는다. 서버 CORS, Supabase URL, service role key, timeout처럼 결과 의미보다 연결/운영에 가까운 값은 첫 범위에서 제외한다.
- snapshot 값은 product code가 실제로 소비한 runtime 원천에서 온다. 기록용 값과 실행용 값이 따로 존재하면 안 된다.
- prompt snapshot은 03의 `prompt_snapshot` safe facts와 같은 identity를 참조하거나 같은 summary로 연결한다.
- public API 응답에는 runtime config, observation, debug, raw payload를 추가하지 않는다.

## Rules

- runtime config snapshot은 product path를 관찰하는 side effect다. material status나 question status를 결정하는 주체가 되면 안 된다.
- snapshot shape의 소유자는 LangSmith adapter가 아니라 material/question runtime이다.
- snapshot은 원본 prompt body, SourceUnit text, retrieval 후보(RetrievedSource) 전문, embedding vector, provider raw response, secret 값을 저장하지 않는다.
- retrieval snapshot은 backend, top-k, similarity threshold처럼 후보 선택을 바꾸는 값을 남긴다.
- embedding snapshot은 auto-generate 여부, provider, model, dimensions처럼 source unit embedding 생성과 query embedding 가능성을 바꾸는 값을 남긴다.
- prompt snapshot은 domain, name, version, body hash, file hash, asset path summary만 남긴다.
- answer composer backend/model은 composer가 노출하는 runtime identity(현재 backend는 `ollama` 고정, model은 `OLLAMA_ANSWER_MODEL`)에서 온다. 다만 provider-neutral answer runtime이 생기기 전까지 route가 provider detail을 임의 추정해 채우지는 않는다.
- snapshot 생성 실패나 sink 실패는 material upload, question answer, exception propagation을 바꾸지 않는다.

## Non-goals

- LangSmith trace export는 이 문서의 범위가 아니다.
- observation record 저장소의 장기 보관, 검색 UI는 정하지 않는다.
- prompt admin UI나 DB 기반 config registry는 만들지 않는다.
- secret, raw request payload, raw LLM payload, raw embedding vector를 저장하지 않는다.
- eval runner나 run artifact를 product code가 import하게 만들지 않는다.

## 현재 코드에서 볼 곳

- `apps/server/core/config.py`: retrieval, embedding, answer composer 관련 env constant의 현재 원천이다.
- `apps/server/app.py`: config 값을 app state의 material store, retrieval repository, answer composer로 wiring한다.
- `apps/server/materials/store.py`: embedding provider/profile/auto-generate와 retrieval repository를 사용해 ready material을 만든다.
- `apps/server/retrieval/search.py`: `RAG_TOP_K`, `RAG_SIMILARITY_THRESHOLD`, vector 검색/lexical fallback 경계다.
- `apps/server/runtime/config_snapshot.py`: runtime config settings와 safe snapshot dataclass를 정의한다.
- `apps/server/materials/observation.py`: material upload observation record가 runtime config snapshot을 직접 가진다.
- `apps/server/questions/observation.py`: question observation의 prompt snapshot safe facts 패턴이다.
- `apps/server/prompts/runtime/prompt_document.py`: prompt document snapshot의 identity 원천이다.
- `apps/server/answers/library_chat.py`: 현재 answer composer backend/model config를 소비하는 경계다.

## 구현면 펼치기

| 구현 요소 | 필요한 이유 | 현재 코드/문서 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Runtime config snapshot model | material/question record가 같은 실행 조건을 참조해야 한다 | `runtime/config_snapshot.py`에 safe snapshot dataclass가 있다 | result-changing knob만 담는 내부 snapshot record가 있다 |
| Config source boundary | 기록용 값과 실행용 값이 갈라지면 snapshot이 거짓이 된다 | `core/config.py`의 flat constant를 app/store/retrieval/composer가 나눠 소비한다 | product code가 실제 소비한 값에서 snapshot을 만든다 |
| Material upload 연결 | upload 결과는 embedding 생성과 repository backend 조건에 영향을 받는다 | material observation은 source/embedding/upsert fact를 남긴다 | material upload record가 embedding/retrieval config snapshot과 연결된다 |
| Question answer 연결 | 답변 결과는 retrieval limit/threshold/backend, prompt identity에 영향을 받는다 | question observation은 retrieval fact와 prompt snapshot fact를 남긴다 | question record가 retrieval/prompt/runtime config snapshot과 연결된다 |
| Safe field allowlist | snapshot이 secret/raw/debug 저장 경로가 되면 안 된다 | observation record는 step별 allowlist를 둔다 | snapshot field도 allowlist로 제한한다 |
| Tests | override된 runtime knob이 snapshot에 반영되어야 한다 | tests는 app/store override와 in-memory sink를 쓴다 | public response 유지와 internal snapshot만 확인한다 |

## 처음 snapshot 후보

첫 구현은 nested object나 provider abstraction을 크게 만들기보다, material/question record가 참조할 수 있는 safe snapshot으로 닫는다.

```text
runtime_config_snapshot
  retrieval
    backend
    top_k
    similarity_threshold
  embedding
    auto_generate
    provider
    model
    dimensions
  prompt
    domain
    name
    version
    body_hash
    file_hash
    asset_path
  answer_model
    backend
    model
```

`answer_model.backend`와 `answer_model.model`은 answer composer가 노출하는 runtime identity(`runtime_answer_model_snapshot`)에서 남긴다. 현재 backend는 `ollama`, model은 `OLLAMA_ANSWER_MODEL`이다. route가 provider detail을 임의 추정해 채우지는 않는다.

## 이번 AC

1. `POST /api/materials`는 기존 public response를 유지하면서 internal material upload observation record와 연결 가능한 runtime config snapshot을 만들 수 있다.
2. `POST /api/questions`는 기존 public response를 유지하면서 retrieval backend/top-k/threshold, embedding profile, prompt identity를 포함한 runtime config snapshot을 만들 수 있다.
3. snapshot 값은 product path가 실제 소비한 runtime source에서 오며, 테스트 override 값도 snapshot에 반영된다.
4. snapshot에는 secret, raw prompt body, SourceUnit text, retrieval 후보(RetrievedSource) 전문, embedding vector, raw provider response가 들어가지 않는다.
5. LangSmith/export adapter 없이도 snapshot 생성과 observation 연결이 닫힌다.

## 구현 결과

2026-06-11 현재 이 slice는 `apps/server/runtime/config_snapshot.py`, app state wiring, material/question observation record 연결로 구현됐다.

`RuntimeConfigSettings`는 app이 실제로 사용할 retrieval backend, retrieval top-k, similarity threshold, embedding auto-generate, embedding profile을 담는다. `POST /api/questions`는 이 settings의 top-k와 threshold를 `retrieve_context_with_trace()`에 직접 넘기므로, snapshot 값과 실제 retrieval 실행 값이 갈라지지 않는다.

material/question observation record는 `runtime_config_snapshot`을 직접 가진다. 아직 별도 snapshot store나 export adapter가 없으므로 id만 연결하지 않고, record 안에 safe snapshot을 embed한다.

snapshot 구조는 다음 값만 포함한다.

```text
runtime_config_snapshot
  retrieval
    backend
    top_k
    similarity_threshold
  embedding
    auto_generate
    provider
    model
    dimensions
  prompt
    domain
    name
    version
    body_hash
    file_hash
    asset_path
  answer_model
    backend
    model
```

`prompt`와 `answer_model`은 해당 runtime이 identity를 노출할 때만 채운다. fake/test composer처럼 identity를 노출하지 않는 경우에는 `None`으로 둔다. API 응답에는 `runtimeConfig`, `observation`, `debug`, `raw`를 추가하지 않는다.

## 구현 중 주의할 점

- snapshot을 API 응답의 개발자 전용 필드로 넣지 않는다.
- 먼저 snapshot 내용물을 닫고, local observation artifact나 LangSmith export는 이후 sink/export slice로 둔다.
- retrieval top-k와 similarity threshold는 app state의 `RuntimeConfigSettings`에서 question route와 snapshot builder가 같이 읽는다.
- embedding auto-generate가 꺼진 경우에도 provider/model/dimensions profile은 pending embedding record의 identity를 바꿀 수 있으므로 snapshot에 남긴다.
- prompt snapshot은 03의 `prompt_snapshot` leaf와 중복될 수 있다. 중복 저장보다 같은 identity를 같은 safe field로 맞추는 것이 중요하다.

## 확인 방법

1. `uv run pytest apps/server/tests/test_materials_api.py`
2. `uv run pytest apps/server/tests`
3. app/store override로 retrieval backend, top-k/threshold, embedding auto-generate/profile을 바꿨을 때 internal snapshot 값만 바뀌는지 확인한다.
4. API 응답 payload에 `observation`, `runtimeConfig`, `debug`, raw retrieval 후보(RetrievedSource), raw LLM JSON field가 추가되지 않았는지 확인한다.

현재 확인된 테스트:

- `uv run pytest apps/server/tests/test_materials_api.py`
- `uv run pytest apps/server/tests`

## 남은 판단

- material/question이 같은 snapshot instance를 공유할지, operation마다 snapshot을 만들지.
- upload size limit처럼 material acceptance를 바꾸는 값까지 첫 snapshot에 포함할지.
- external exporter에서 file name, prompt asset path 같은 safe field를 더 줄여야 하는지.
