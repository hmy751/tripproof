# Question execution 관측 record

작성일: 2026-06-11

상태: 구현된 하위 작업 spec. `POST /api/questions`의 question preparation, material scope, retrieval pipeline, answer pipeline, finalization 경계를 내부 observation record로 남기는 기준을 정한다.

## 왜 지금

`POST /api/materials`는 upload, parse, source unit, embedding, retrieval repository upsert 경계를 내부 record로 남긴다. 이제 자료함 질문 결과가 흔들렸을 때 답변만 보면 어떤 ready material이 질문에 들어갔는지, retrieval이 실제 실행됐는지, answer composer가 어떤 결과를 냈는지 확인하기 어렵다.

이 slice에서는 LangSmith나 runtime config snapshot을 먼저 붙이지 않는다. `/api/questions` product path에서 실제로 생기는 실행 fact를 내부 record로 남기고, prompt identity는 composer가 노출할 때 safe facts로 남긴다. 외부 trace나 runtime config snapshot은 이후 이 record를 소비하거나 연결되는 계층으로 둔다.

## 사용자 장면

사용자가 ready 상태의 여행 자료를 두고 자료함에 질문한다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

API 응답은 기존처럼 `accepted` 또는 `blocked` question response다. 개발자는 사용자-facing 응답에 raw debug를 섞지 않고도 다음 경계를 확인할 수 있어야 한다.

- 질문에 들어간 ready material이 몇 개인가.
- 질문에 들어간 ready material id는 무엇인가.
- retrieval record load가 성공했는가.
- SourceUnit retrieval이 어떤 전략으로 실행됐고, retrieval 후보 요약(`candidate_summary`)은 어떤가.
- answer composer에 prompt snapshot이 연결됐는가.
- answer composer 호출과 answer projection이 route 관점에서 성공했는가, 실패했는가.
- 최종 question status가 `accepted`인지 `blocked`인지.
- 실패했다면 최소 failure kind가 무엇인가.

## Goal

- `POST /api/questions` 한 요청에 대응하는 question execution observation record를 만들 수 있다.
- 이 slice는 adapter나 공통 tracing wrapper가 아니라 product path에서 question execution fact를 생성하는 leaf producer를 구현한다.
- record는 question preparation, material scope, retrieval pipeline, answer pipeline, finalization 경계를 담는다.
- `accepted`/`blocked` question 응답의 public contract는 바꾸지 않는다.
- observation record는 SourceUnit text, retrieval 후보(RetrievedSource) 전문, answer body 전문, LLM raw payload, exception stack을 저장하지 않는다.
- 관측 record 생성 실패나 비활성화가 question response 결과를 바꾸지 않는다.

## Rules

- observation은 product path를 관찰하는 side effect다. question status를 결정하는 주체가 되면 안 된다.
- record shape의 소유자는 adapter가 아니라 `/api/questions` execution event다.
- question preparation은 질문 원문이 아니라 정규화된 질문 길이 같은 safe summary만 남긴다.
- ready material selection은 `ready_material_count`와 `ready_material_ids`까지만 남긴다.
- ready material이 없어 `blocked`가 되면 retrieval과 answer composer는 실행되지 않은 상태로 남긴다.
- material scope는 ready material selection과 retrieval record load를 구분한다.
- retrieval pipeline은 `source_retrieval`, `AnswerContext` assembly, retrieval 후보 요약(`candidate_summary`)을 구분한다. RetrievedSource 후보 text, SourceUnit text, score 상세 목록은 기본 record에 넣지 않는다.
- answer pipeline은 prompt snapshot, composer call, answer projection을 구분한다. provider raw response나 LLM 내부 실패 payload를 route record가 추정해 채우지 않는다.
- composer가 missing answer를 정상 `ChatAnswerResponse`로 반환하면 route 관점의 composer 호출 결과는 `succeeded`다.
- retrieval 또는 answer composer가 예외를 내면 기존 public error behavior를 바꾸지 않고, record에는 실패 boundary와 failure kind를 요약한다.
- sink가 실패해도 question response, exception propagation, material store 상태를 바꾸지 않는다.

## Non-goals

- LangSmith trace export는 이 문서의 범위가 아니다.
- provider/model/retrieval config snapshot 전체를 확정하지 않는다.
- runtime config snapshot 전체 연결은 이 문서의 범위가 아니다.
- composer 내부 provider call, prompt render, raw LLM payload 관측은 만들지 않는다.
- observation record 저장소의 장기 보관, 검색 UI는 정하지 않는다.
- question API 응답에 debug field, retrieval 후보(RetrievedSource), observation field를 추가하지 않는다.

## 현재 코드에서 볼 곳

- `apps/server/api/routes/questions.py`: `/api/questions`가 ready material, retrieval records, `retrieve_context_with_trace`, answer composer, `QuestionResponse`를 연결한다.
- `apps/server/api/deps.py`: material store, answer composer, question observation sink dependency를 제공한다.
- `apps/server/app.py`: 기본 no-op sink와 테스트용 sink를 app state에 연결한다.
- `apps/server/questions/observation.py`: question observation record, recorder, sink, safe facts allowlist를 정의한다.
- `apps/server/materials/observation.py`: material upload observation의 step model, sink protocol, no-op/in-memory sink, safe facts allowlist 패턴이다.
- `apps/server/materials/store.py`: ready material과 retrieval record를 조회하는 경계다.
- `apps/server/retrieval/search.py`: `retrieve_context_with_trace`가 answer composer에 넘길 `AnswerContext`와 source retrieval summary를 만든다.
- `apps/server/answers/library_chat.py`: `LibraryChatAnswerComposer.compose` 계약과 `ChatAnswerResponse` 생성 경계다.
- `apps/server/schemas/questions.py`: public `QuestionResponse` status 계약이다.
- `apps/server/tests/test_materials_api.py`: 현재 question route 테스트와 material observation 테스트가 함께 있다.

## 구현면 펼치기

| 구현 요소 | 필요한 이유 | 현재 코드/문서 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Question observation model | 한 질문 요청의 관측 결과를 안정된 형태로 남겨야 한다 | `questions/observation.py` | question preparation, material scope, retrieval pipeline, answer pipeline, finalization을 담는 계층형 ordered step record가 있다 |
| Observation sink | record 생성과 저장 방식을 product logic에서 분리해야 한다 | material upload는 no-op/in-memory sink 패턴을 쓴다 | 기본 no-op sink와 테스트용 in-memory sink가 있고 비활성화 시 응답이 바뀌지 않는다 |
| Route boundary capture | ready material count/id, retrieval record load, SourceUnit retrieval, `AnswerContext` assembly, composer 호출 결과는 route가 연결한다 | `routes/questions.py`가 product path를 모두 연결한다 | blocked/accepted/exception 경계에서 record가 finalize된다 |
| Failure summary | 실패를 나중에 비교하려면 최소 failure kind가 필요하다 | question route에는 아직 내부 failure kind가 없다 | `empty_question`, `no_ready_materials`, `retrieval_failed`, `answer_composer_failed`를 구분한다 |
| Safe facts allowlist | raw SourceUnit text, raw answer, provider payload가 새지 않아야 한다 | material observation은 step별 allowlist를 둔다 | step별 허용 fact만 record에 남긴다 |
| Tests | record가 product response를 오염시키지 않아야 한다 | `test_materials_api.py`에 question route 테스트가 있다 | accepted/blocked 응답은 유지되고 internal record만 추가로 확인한다 |

## 처음 record shape

내부 record는 한 요청을 계층형 ordered step으로 남긴다.

```text
question_answer
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

각 step은 `not_started`, `succeeded`, `failed` 중 하나의 status를 가진다. parent step의 status는 child step 결과에서 파생된다. step별 facts는 allowlist로 제한한다.

여기서 `candidate_summary`는 extraction 후보(FactCandidate)가 아니라 `AnswerContext.candidates`에 들어간 retrieval 후보(RetrievedSource)의 count/score-presence 요약이다.

| Step | 남기는 facts | 실패 예 |
| --- | --- | --- |
| `query_snapshot` | `question_length` | `empty_question` |
| `ready_material_selection` | `ready_material_count`, `ready_material_ids` | `no_ready_materials` |
| `retrieval_record_load` | `executed`, `source_unit_count`, `embedding_record_count` | `retrieval_failed` |
| `source_retrieval` | `executed`, `query_embedding_attempted`, `query_embedding_available`, `vector_attempted`, `vector_candidate_count`, `fallback_used` | `retrieval_failed` |
| `context_assembly` | `executed`, `target_id` | `retrieval_failed` |
| `candidate_summary` | `candidate_count`, `candidates_with_vector_score`, `candidates_with_lexical_score` | 없음 |
| `prompt_snapshot` | `available`, `prompt_domain`, `prompt_name`, `prompt_version`, `prompt_body_hash`, `prompt_file_hash`, `prompt_asset_path` | 없음 |
| `composer_call` | `result` | `answer_composer_failed` |
| `answer_projection` | `item_count`, `evidence_state_counts` | 없음 |
| `question_status` | `status` | 없음 |

top-level record는 `final_question_status`를 `accepted`, `blocked`, 또는 예외로 응답이 완성되지 않은 경우 `None`으로 남긴다. `failure_kind`는 필요한 경우만 최소 구분으로 남긴다.

`empty_question`은 현재 route가 `400`을 반환하는 request failure다. route 진입 이후 recorder를 만들 수 있으므로 `query_snapshot` failure, final status `None`, failure kind `empty_question`으로 남긴다.

`query_rewrite`, `rerank`, `judge`, `answer_grounding`처럼 이후 추가될 수 있는 pipeline은 현재 record에 가짜 step으로 넣지 않는다. 구현되면 `question_preparation`, `retrieval_pipeline`, `answer_pipeline` 중 실제 책임 위치 아래에 leaf step으로 추가한다.

## 관측 기준

`question_answer` record는 답변 상태를 만든 AI/runtime 경로를 복원하기 위한 지도다. 서버 함수 호출 로그나 LLM raw trace가 아니라, material scope, retrieval/RAG가 만든 `AnswerContext`, prompt/composer 조건, answer projection을 안전한 summary로 남긴다.

이 record는 다음 질문에 답할 수 있어야 한다.

- AI/composer가 읽을 `AnswerContext`는 어떤 material scope와 retrieval/RAG 경로에서 준비됐는가.
- AI/composer는 어떤 prompt identity와 조건에서 호출됐는가.
- composer 결과가 제품 answer state로 어떻게 projection됐는가.
- 최종 question status가 왜 `accepted`, `blocked`, 또는 예외 미완료 상태가 됐는가.

`step`은 AI/runtime 판단이나 answer 결과를 바꾸는 안정된 pipeline boundary다. provider나 내부 구현이 바뀌어도 제품 의미의 이름이 유지될 수 있어야 한다.

`fact`는 step 안의 safe summary다. strategy, mode, count, hash, status처럼 원인 추적에는 필요하지만 독립 stage로 보기엔 작은 값은 fact로 둔다.

parent step은 영역을 나누고, leaf step은 실제 제품 fact를 만든다. 관측은 leaf 중심으로 찍고 parent status는 leaf 결과에서 파생한다.

현재 구조는 이 감각이다.

```text
question_answer
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

`source_retrieval`은 step이지만, `lexical fallback`은 지금 단계에서는 `source_retrieval`의 fact에 가깝다. 예: `vector_attempted`, `vector_candidate_count`, `fallback_used`. rerank, judge, grounding check가 실제 product module로 들어와 후보 순서나 answer state를 바꾸면 독립 step으로 승격한다.

step/fact 판단 기준은 함수 크기나 route visibility가 아니라 AI/runtime 원인 추적력이다. raw SourceUnit text, embedding vector, raw LLM payload, exception stack은 기본 record에 넣지 않는다. 필요하면 id/count/hash/status summary만 남긴다.

## 이번 AC

1. ready material이 있는 질문은 기존 `accepted` 응답을 유지하면서 query snapshot, ready material count/id, retrieval record load, `source_retrieval`, `AnswerContext` assembly, retrieval 후보 요약(`candidate_summary`), prompt snapshot availability, composer call, answer projection, final question status `accepted`를 담은 internal observation record를 만든다.
2. ready material이 없는 질문은 기존 `blocked` 응답을 유지하면서 ready material count `0`, material ids `[]`, final question status `blocked`, failure kind `no_ready_materials`를 담은 internal observation record를 만든다.
3. retrieval 또는 answer composer가 예외를 내면 기존 public 동작을 바꾸지 않고, 관측 가능한 실패 boundary와 failure kind를 record에 요약한다.
4. observation record에는 SourceUnit text, retrieval 후보(RetrievedSource) 전문, answer body 전문, LLM raw payload, exception stack이 들어가지 않는다.
5. observation sink가 비활성화되거나 실패해도 `POST /api/questions`의 product 응답 계약은 동일하다.

## 구현 결과

2026-06-11 현재 이 slice는 `apps/server/questions/observation.py`와 `/api/questions` route 연결로 구현됐다.

내부 record는 한 요청을 parent/leaf step으로 남긴다. 부모 단계는 제품 파이프라인을 읽기 위한 묶음이고, leaf 단계가 실제 code boundary에서 생긴 fact를 가진다.

```text
question_answer
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

기본 sink는 no-op이고, 테스트에서는 in-memory sink로 record를 확인한다. sink가 실패해도 product 응답, 예외 propagation, material store 상태를 바꾸지 않는다.

## 구현 중 주의할 점

- route-level `composer_call` result는 composer 내부 provider 성공 여부가 아니라 `compose()` 호출이 `ChatAnswerResponse`를 반환했는지에 대한 관측이다.
- retrieval 후보 count는 `AnswerContext.candidates` 길이로 시작한다. vector/lexical 세부는 `source_retrieval`의 vector_attempted/vector_candidate_count/fallback_used summary와 `candidate_summary`의 count까지만 남긴다.
- material id 목록은 ready material id만 남긴다. 요청 payload에 들어왔지만 failed이거나 존재하지 않는 material id를 별도 진단하는 것은 다음 slice다.
- prompt snapshot은 composer가 prompt identity를 노출할 때만 version/hash/asset path summary를 남긴다. prompt 전문은 저장하지 않는다.
- config snapshot은 이 record와 나중에 연결할 수 있지만, 이번 record가 config snapshot 없이도 닫히도록 둔다.

## 확인 방법

1. `uv run pytest apps/server/tests/test_materials_api.py`
2. ready PDF 업로드 후 `/api/questions` accepted response와 internal observation record를 함께 확인한다.
3. failed material만 있는 상태에서 `/api/questions` blocked response와 failure kind record를 확인한다.
4. answer composer 예외 테스트에서 기존 exception behavior와 failure boundary record를 확인한다.
5. API 응답 payload에 observation/debug/raw retrieval 후보(RetrievedSource) field가 추가되지 않았는지 확인한다.

## 남은 판단

- request payload의 requested material ids를 record에 둘지, ready material ids만 둘지.
- candidate count 외에 retrieval 후보의 SourceUnit id 목록까지 안전한 summary로 볼지.
- question observation record와 runtime config snapshot을 같은 record 안에 붙일지, 별도 snapshot id로 연결할지.
- requested material ids를 나중에 별도 diagnostic snapshot으로 볼지, ready material selection fact만 유지할지.
