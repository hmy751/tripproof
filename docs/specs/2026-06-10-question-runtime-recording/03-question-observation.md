# Question execution 관측 record

작성일: 2026-06-11

상태: 하위 작업 spec. `POST /api/questions`의 ready material 선택, retrieval 실행, answer composer 호출, 최종 question status 경계를 내부 observation record로 남기는 기준을 정한다.

## 왜 지금

`POST /api/materials`는 upload, parse, source unit, embedding, retrieval repository upsert 경계를 내부 record로 남긴다. 이제 자료함 질문 결과가 흔들렸을 때 답변만 보면 어떤 ready material이 질문에 들어갔는지, retrieval이 실제 실행됐는지, answer composer가 어떤 결과를 냈는지 확인하기 어렵다.

이 slice에서는 LangSmith나 config/prompt snapshot을 먼저 붙이지 않는다. `/api/questions` product path에서 실제로 생기는 실행 fact를 내부 record로 남기고, 외부 trace나 snapshot은 이후 이 record를 소비하는 계층으로 둔다.

## 사용자 장면

사용자가 ready 상태의 여행 자료를 두고 자료함에 질문한다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

API 응답은 기존처럼 `accepted` 또는 `blocked` question response다. 개발자는 사용자-facing 응답에 raw debug를 섞지 않고도 다음 경계를 확인할 수 있어야 한다.

- 질문에 들어간 ready material이 몇 개인가.
- 질문에 들어간 ready material id는 무엇인가.
- retrieval이 실행됐는가.
- retrieval 결과 answer composer에 전달된 candidate가 몇 개인가.
- answer composer 호출이 route 관점에서 성공했는가, 실패했는가.
- 최종 question status가 `accepted`인지 `blocked`인지.
- 실패했다면 최소 failure kind가 무엇인가.

## Goal

- `POST /api/questions` 한 요청에 대응하는 question execution observation record를 만들 수 있다.
- 이 slice는 adapter나 공통 tracing wrapper가 아니라 product path에서 question execution fact를 생성하는 leaf producer를 구현한다.
- record는 ready material selection, retrieval, answer composer, final question status 경계를 담는다.
- `accepted`/`blocked` question 응답의 public contract는 바꾸지 않는다.
- observation record는 source unit text, retrieval candidate 전문, answer body 전문, LLM raw payload, exception stack을 저장하지 않는다.
- 관측 record 생성 실패나 비활성화가 question response 결과를 바꾸지 않는다.

## Rules

- observation은 product path를 관찰하는 side effect다. question status를 결정하는 주체가 되면 안 된다.
- record shape의 소유자는 adapter가 아니라 `/api/questions` execution event다.
- ready material selection은 `ready_material_count`와 `ready_material_ids`까지만 남긴다.
- ready material이 없어 `blocked`가 되면 retrieval과 answer composer는 실행되지 않은 상태로 남긴다.
- retrieval step은 실행 여부와 retrieved candidate count를 남긴다. candidate text, source unit text, score 상세 목록은 기본 record에 넣지 않는다.
- answer composer step은 route가 관찰할 수 있는 호출 결과만 남긴다. provider raw response나 LLM 내부 실패 payload를 route record가 추정해 채우지 않는다.
- composer가 missing answer를 정상 `ChatAnswerResponse`로 반환하면 route 관점의 composer 호출 결과는 `succeeded`다.
- retrieval 또는 answer composer가 예외를 내면 기존 public error behavior를 바꾸지 않고, record에는 실패 boundary와 failure kind를 요약한다.
- sink가 실패해도 question response, exception propagation, material store 상태를 바꾸지 않는다.

## Non-goals

- LangSmith trace export는 이 문서의 범위가 아니다.
- provider/model/retrieval config snapshot 전체를 확정하지 않는다.
- prompt version/hash snapshot 연결은 이 문서의 범위가 아니다.
- composer 내부 provider call, prompt render, raw LLM payload 관측은 만들지 않는다.
- observation record 저장소의 장기 보관, 검색 UI, 개인정보 마스킹 정책은 정하지 않는다.
- question API 응답에 debug field, retrieval candidates, observation field를 추가하지 않는다.

## 현재 코드에서 볼 곳

- `apps/server/api/routes/questions.py`: `/api/questions`가 ready material, retrieval records, `retrieve_context`, answer composer, `QuestionResponse`를 연결한다.
- `apps/server/api/deps.py`: material store와 answer composer dependency를 제공한다. question observation sink dependency를 추가할 위치다.
- `apps/server/app.py`: 기본 no-op sink와 테스트용 sink를 app state에 연결할 위치다.
- `apps/server/materials/observation.py`: material upload observation의 step model, sink protocol, no-op/in-memory sink, safe facts allowlist 패턴이다.
- `apps/server/materials/store.py`: ready material과 retrieval record를 조회하는 경계다.
- `apps/server/retrieval/search.py`: `retrieve_context`가 answer composer에 넘길 `ContextPack` 후보를 만든다.
- `apps/server/answers/library_chat.py`: `LibraryChatAnswerComposer.compose` 계약과 `ChatAnswerResponse` 생성 경계다.
- `apps/server/schemas/questions.py`: public `QuestionResponse` status 계약이다.
- `apps/server/tests/test_materials_api.py`: 현재 question route 테스트와 material observation 테스트가 함께 있다.

## 구현면 펼치기

| 구현 요소 | 필요한 이유 | 현재 코드/문서 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Question observation model | 한 질문 요청의 관측 결과를 안정된 형태로 남겨야 한다 | 새 `questions/observation.py`가 필요하다 | ready material, retrieval, answer composer, final status를 담는 ordered step record가 있다 |
| Observation sink | record 생성과 저장 방식을 product logic에서 분리해야 한다 | material upload는 no-op/in-memory sink 패턴을 쓴다 | 기본 no-op sink와 테스트용 in-memory sink가 있고 비활성화 시 응답이 바뀌지 않는다 |
| Route boundary capture | ready material count/id, retrieval 실행 여부, composer 호출 결과는 route가 연결한다 | `routes/questions.py`가 product path를 모두 연결한다 | blocked/accepted/exception 경계에서 record가 finalize된다 |
| Failure summary | 실패를 나중에 비교하려면 최소 failure kind가 필요하다 | question route에는 아직 내부 failure kind가 없다 | `empty_question`, `no_ready_materials`, `retrieval_failed`, `answer_composer_failed`를 구분한다 |
| Safe facts allowlist | raw source, raw answer, provider payload가 새지 않아야 한다 | material observation은 step별 allowlist를 둔다 | step별 허용 fact만 record에 남긴다 |
| Tests | record가 product response를 오염시키지 않아야 한다 | `test_materials_api.py`에 question route 테스트가 있다 | accepted/blocked 응답은 유지되고 internal record만 추가로 확인한다 |

## 처음 record shape

내부 record는 한 요청을 ordered step으로 남긴다.

```text
question_answer
  ready_material_selection
  retrieval
  answer_composer
```

각 step은 `not_started`, `succeeded`, `failed` 중 하나의 status를 가진다. step별 facts는 allowlist로 제한한다.

| Step | 남기는 facts | 실패 예 |
| --- | --- | --- |
| `ready_material_selection` | `ready_material_count`, `ready_material_ids` | `no_ready_materials` |
| `retrieval` | `executed`, `candidate_count` | `retrieval_failed` |
| `answer_composer` | `result`, `item_count`, `evidence_state_counts` | `answer_composer_failed` |

top-level record는 `final_question_status`를 `accepted`, `blocked`, 또는 예외로 응답이 완성되지 않은 경우 `None`으로 남긴다. `failure_kind`는 필요한 경우만 최소 구분으로 남긴다.

`empty_question`은 현재 route가 `400`을 반환하는 validation failure다. 이 경우 observation을 남길지 여부는 구현에서 route 진입 이후 recorder를 만들 수 있는지에 따라 결정한다. 남긴다면 final status는 `None`, failure kind는 `empty_question`으로 둔다.

## 이번 AC

1. ready material이 있는 질문은 기존 `accepted` 응답을 유지하면서 ready material count/id, retrieval executed, retrieved candidate count, answer composer result, final question status `accepted`를 담은 internal observation record를 만든다.
2. ready material이 없는 질문은 기존 `blocked` 응답을 유지하면서 ready material count `0`, material ids `[]`, final question status `blocked`, failure kind `no_ready_materials`를 담은 internal observation record를 만든다.
3. retrieval 또는 answer composer가 예외를 내면 기존 public 동작을 바꾸지 않고, 관측 가능한 실패 boundary와 failure kind를 record에 요약한다.
4. observation record에는 source unit text, retrieval candidate 전문, answer body 전문, LLM raw payload, exception stack이 들어가지 않는다.
5. observation sink가 비활성화되거나 실패해도 `POST /api/questions`의 product 응답 계약은 동일하다.

## 구현 중 주의할 점

- route-level `answer_composer` result는 composer 내부 provider 성공 여부가 아니라 `compose()` 호출이 `ChatAnswerResponse`를 반환했는지에 대한 관측이다.
- retrieved candidate count는 `ContextPack.candidates` 길이로 충분히 시작한다. vector match인지 lexical fallback인지는 이번 slice에서 추정하지 않는다.
- material id 목록은 ready material id만 남긴다. 요청 payload에 들어왔지만 failed이거나 존재하지 않는 material id를 별도 진단하는 것은 다음 slice다.
- prompt/config snapshot은 이 record와 나중에 연결할 수 있지만, 이번 record가 prompt/config snapshot 없이도 닫히도록 둔다.

## 확인 방법

1. `uv run pytest apps/server/tests/test_materials_api.py`
2. ready PDF 업로드 후 `/api/questions` accepted response와 internal observation record를 함께 확인한다.
3. failed material만 있는 상태에서 `/api/questions` blocked response와 failure kind record를 확인한다.
4. answer composer 예외 테스트에서 기존 exception behavior와 failure boundary record를 확인한다.
5. API 응답 payload에 observation/debug/raw/retrieval candidate field가 추가되지 않았는지 확인한다.

## 남은 판단

- `empty_question` 같은 request validation failure까지 question observation record로 남길지.
- request payload의 requested material ids를 record에 둘지, ready material ids만 둘지.
- candidate count 외에 candidate source unit id 목록까지 안전한 summary로 볼지.
- composer result에 `evidence_state_counts`를 둘지, item count만 먼저 둘지.
- question observation record와 prompt/config snapshot을 같은 record 안에 붙일지, 별도 snapshot id로 연결할지.
