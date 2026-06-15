# Server readable-flow refactor

작성일: 2026-06-15

상태: 리팩터링 기준 spec. 2026-06-15 1차 서버 refactor 결과를 기준점으로 삼아 후속 readable-flow refactor의 판단 기준을 정리한다.

## 왜 지금

TripProof 서버는 사용자가 자료를 올리고 자료함에 질문해 근거가 붙은 답변을 받는 product path를 갖고 있다. 이 흐름은 `route -> use case -> material store/retrieval -> answer composer -> observation/export`를 지나지만, 기존 구조에서는 route, retrieval, composer, observation 경계가 한눈에 읽히기 어렵고 내부 타입명과 변수명이 독자에게 현재 층위를 충분히 설명하지 못했다.

이번 refactor의 목적은 route를 얇게 만드는 것만이 아니다. 동작을 함부로 바꾸지 않으면서도, 낮은 위험의 구조 정리와 이름 정리로 판단 경계를 드러내는 것이다. 코드를 읽는 사람이 다음 질문에 답할 수 있어야 한다.

- HTTP adapter가 맡는 일과 product 흐름을 실행하는 use case의 일이 분리되어 있는가.
- 자료 업로드에서 `upload -> parse -> retrieval record preparation -> ready/failed material` 흐름이 순서대로 보이는가.
- 질문 응답에서 `question -> ready material selection -> retrieval -> answer context -> composer -> response` 흐름이 순서대로 보이는가.
- AI/RAG 경계에서 retrieval, answer projection, payload validation, observation이 서로의 책임을 덮지 않는가.
- observation은 product 응답을 바꾸지 않고 실행 조건을 복원할 만큼의 safe fact만 남기는가.

## 범위 경계

이 spec의 기준 재료는 2026-06-15 서버 refactor 커밋들과 서버 코드의 readable-flow 경계다.

이 문서는 product behavior를 새로 완료했다고 선언하지 않는다. 기본 API 응답과 사용자-facing answer contract는 유지하면서, 서버 내부 흐름을 읽고 판단하기 쉬운 구조로 옮기는 기준을 둔다.

## 개발자 장면

개발자가 `POST /api/materials` 또는 `POST /api/questions`의 실패, 응답 변화, observation record를 추적한다. 개발자는 route 파일 하나에서 모든 판단을 읽는 대신, route가 HTTP adapter 역할을 하는지 확인하고 use case와 domain service를 따라가며 다음을 분리해 볼 수 있어야 한다.

- 입력 정규화와 HTTP 오류 변환.
- product 흐름의 실행 순서.
- retrieval record 생성과 retrieval strategy 선택.
- answer composer 입력 context와 output payload projection.
- observation step과 safe fact projection.
- API response body에 노출하지 않을 trace/runtime/debug 정보.

## Goal

- route는 dependency wiring, request read, HTTP 예외 변환, response 반환 중심으로 남긴다.
- use case는 product 흐름의 주요 판단 순서를 드러내고, HTTP 없이도 테스트할 수 있다.
- 자료 업로드 경로는 parse, source unit, embedding record, retrieval repository upsert, ready/failed material 경계를 observation과 함께 읽을 수 있다.
- 질문 응답 경로는 ready material selection, retrieval record load, retrieval strategy, answer context assembly, composer call, answer projection 경계를 읽을 수 있다.
- `AnswerContext`, `RetrievedSource`, `SourceRetrievalTrace`, `NormalizedAnswerItemPayload` 같은 이름은 현재 값이 어느 층위의 산물인지 설명한다.
- observation은 실행 흐름을 복원할 safe fact를 남기되, raw question, raw source text, raw LLM payload, runtime config를 product response body에 섞지 않는다.
- refactor 후에도 기존 API behavior와 서버 테스트 기준은 유지한다.

## Non-goals

- API response shape를 새 기능처럼 바꾸지 않는다.
- LLM provider 품질, retrieval ranking 품질, prompt 내용 자체를 이 spec에서 개선 완료로 보지 않는다.
- LangSmith, local artifact, eval run을 product 성공 기준으로 승격하지 않는다.
- 모든 서버 파일을 한 번에 재배치하거나 layer architecture를 새로 도입하지 않는다.
- observation 파일 분리, retrieval/answer 추가 분리는 후보로 남길 수 있지만 이번 1차 refactor에서 완료됐다고 쓰지 않는다.

## 1차 refactor에 반영된 범위

| 커밋 | 반영된 기준 | 현재 코드에서 볼 곳 |
| --- | --- | --- |
| `a656a0d` | 질문 응답 use case 분리. route는 HTTP adapter로 줄고, `AskQuestionUseCase`가 질문 trim, ready material selection, retrieval, composer, observation emission을 실행한다 | `apps/server/api/routes/questions.py`, `apps/server/use_cases/questions.py`, `apps/server/tests/test_question_use_case.py` |
| `57df7fe` | 자료 업로드 use case 분리. route는 upload file read와 HTTP 413 변환을 담당하고, `UploadMaterialUseCase`가 size check, PDF 판별/파싱, failed/ready 저장을 실행한다 | `apps/server/api/routes/materials.py`, `apps/server/use_cases/materials.py`, `apps/server/tests/test_material_upload_use_case.py` |
| `d8b968e` | 답변 context 타입명을 정리해 retrieval 결과가 answer composer 입력 context로 넘어가는 층위를 드러낸다. 기존 호환 alias는 남아 있지만 preferred name은 `AnswerContext`, `RetrievedSource`다 | `apps/server/retrieval/models.py`, `apps/server/retrieval/search.py`, `apps/server/answers/library_chat.py` |
| `1761a62` | 자료 업로드 observation reporter를 분리해 upload/parse/retrieval preparation/finalization step 기록이 use case 흐름에서 읽히게 한다 | `apps/server/materials/observation.py`, `apps/server/use_cases/materials.py` |
| `db593d6` | material storage 내부 source unit/embedding/upsert 단계를 `MaterialIngestionEvents` 경계로 관찰한다. store는 저장과 record 준비를 수행하고, observation 구현에 직접 의존하지 않는다 | `apps/server/materials/ingestion.py`, `apps/server/materials/store.py`, `apps/server/materials/observation.py` |
| `e6ec50d` | retrieval strategy 흐름을 trace와 함께 분리한다. repository vector, local vector, lexical, none 전략과 fallback 여부가 `SourceRetrievalTrace`에 드러난다 | `apps/server/retrieval/search.py`, `apps/server/tests/test_retrieval_search.py` |
| `fee5cf3` | answer composer가 LLM payload의 supported item을 source unit 원문 근거로 투영하는 흐름을 helper 경계로 드러낸다 | `apps/server/answers/library_chat.py`, `apps/server/tests/test_library_chat_answer.py` |
| `9413a16` | answer item payload normalization 경계를 분리한다. raw payload에서 label/body/value/evidence state/source id/snippet을 정규화한 뒤 supported/missing/needs review projection으로 넘긴다 | `apps/server/answers/library_chat.py`, `apps/server/tests/test_library_chat_answer.py` |

## 현재 코드에서 볼 흐름

### Material upload

`POST /api/materials` route는 `UploadFile`에서 filename, content type, bytes, display name을 꺼내 `UploadMaterialUseCase`로 넘긴다. use case는 다음 순서를 갖는다.

1. display name과 file name으로 material name을 정한다.
2. size limit 초과는 `MaterialUploadTooLargeError`로 올리고 route가 HTTP 413으로 변환한다.
3. PDF가 아니면 failed material을 저장하고 unsupported observation을 남긴다.
4. PDF parse 실패는 failed material과 parse failure observation으로 닫는다.
5. parse 성공 후 `MaterialStore.add_ready`가 source unit, embedding record, retrieval repository upsert를 수행한다.
6. `MaterialIngestionEvents`를 통해 source unit build, embedding record build, retrieval repository upsert, ready 상태가 observation에 기록된다.

이 흐름에서 product response는 기존 material schema를 유지한다. observation, debug, raw, runtime config, request/correlation id는 JSON body에 들어가지 않는다.

### Question answer

`POST /api/questions` route는 `AskQuestionUseCase`를 만들고 empty question만 HTTP 400으로 변환한다. use case는 다음 순서를 갖는다.

1. prompt/runtime config snapshot을 만든 뒤 observation reporter를 준비한다.
2. 질문을 trim하고 empty question이면 observation을 남긴 뒤 error를 올린다.
3. ready material이 없으면 blocked response를 만들고 retrieval/composer를 시작하지 않는다.
4. ready material이 있으면 retrieval records를 읽고 source unit/embedding record count를 기록한다.
5. `retrieve_context_with_trace`가 source retrieval strategy와 `AnswerContext`를 함께 반환한다.
6. answer composer는 `AnswerContext`를 받아 `ChatAnswerResponse`를 만든다.
7. use case는 accepted `QuestionResponse`를 만들고 answer projection fact를 observation에 남긴다.

이 흐름에서 retrieval 후보, prompt snapshot, answer projection fact는 observation으로 관찰되지만, raw retrieval candidate나 raw LLM payload가 사용자-facing response처럼 노출되지는 않는다.

## Readable-flow 판단 기준

| 기준 | 좋은 상태 | 냄새 신호 |
| --- | --- | --- |
| Route boundary | route가 HTTP adapter와 dependency wiring을 담당하고 use case에 command를 넘긴다 | route가 retrieval, composer, observation step을 직접 조립한다 |
| Use case boundary | use case가 product 흐름의 순서를 읽히게 하고 HTTP 없이 테스트된다 | use case가 얇은 wrapper라 실제 판단은 다시 route나 helper 깊은 곳에 숨는다 |
| Naming | 이름이 값의 층위를 설명한다. 예: `AnswerContext`는 composer 입력 context, `RetrievedSource`는 retrieval candidate | `context`, `payload`, `source` 같은 이름만으로 raw/provider/domain/response 층위가 구분되지 않는다 |
| Retrieval boundary | strategy, fallback, candidate count가 retrieval trace로 남고 answer composer에는 `AnswerContext`가 넘어간다 | retrieval ranking, prompt rendering, answer validation이 한 함수에서 섞인다 |
| Answer projection | raw answer item은 normalization을 지난 뒤 supported/missing/needs review projection으로 간다 | LLM이 `supported`라고 말한 값을 source unit 원문 검증 없이 그대로 response에 싣는다 |
| Observation boundary | safe fact만 record/export되고 product response body는 유지된다 | observation을 위해 raw question/source/LLM payload나 runtime config가 API body에 들어간다 |
| Test shape | use case tests가 HTTP 없이 흐름과 trace를 확인하고 API tests가 response contract를 확인한다 | API test만 있어 내부 흐름이 바뀌어도 어디가 책임자인지 알기 어렵다 |

## Refactor acceptance 기준

1. `uv run pytest apps/server/tests`가 통과해야 한다.
2. 기존 `/api/materials`와 `/api/questions` response body contract는 refactor 때문에 바뀌지 않아야 한다.
3. route 파일을 읽었을 때 HTTP adapter 역할과 dependency wiring이 중심이어야 한다.
4. use case 파일을 읽었을 때 자료 업로드와 질문 응답의 product 흐름이 순서대로 드러나야 한다.
5. AI/RAG 경계에서 retrieval strategy, answer context, payload normalization, evidence grounding, observation fact projection이 서로 섞이지 않아야 한다.
6. observation 기록/내보내기 실패는 기존 observation/exporter 계약처럼 product response body와 상태 판단에 영향을 주지 않아야 한다.
7. 새 이름이나 helper는 단순 취향이 아니라 reader가 현재 값의 책임과 층위를 판단하는 데 도움을 줘야 한다.

## 남은 후보

아래는 이어갈 수 있는 후보이지 완료된 scope가 아니다.

- `apps/server/materials/observation.py`, `apps/server/questions/observation.py`는 record model, recorder, reporter, safe fact projection을 한 파일에 함께 갖고 있다. 파일이 더 커지면 model/recorder/reporter/projection 분리를 검토한다.
- `apps/server/retrieval/search.py`는 repository vector, local vector, lexical fallback, excerpt helper를 함께 갖고 있다. strategy trace가 더 복잡해지면 retrieval strategy 선택과 local ranking을 분리한다.
- `apps/server/answers/library_chat.py`는 composer, prompt call, answer item normalization, evidence grounding, display fallback을 함께 갖고 있다. payload normalization과 evidence projection이 더 커지면 별도 module로 옮긴다.
- use case trace와 observation record의 관계를 짧은 서버 trace 문서로 설명할지 검토한다. 단, 문서가 product proof나 eval gate처럼 보이면 안 된다.
- API behavior 유지 확인과 내부 readable-flow 확인을 테스트 계층에서 어떻게 나눌지 더 명시할 수 있다.

## 확인한 커밋

- `a656a0d refactor(server): 질문 응답 유스케이스 분리`
- `57df7fe refactor(server): 자료 업로드 유스케이스 분리`
- `d8b968e refactor(server): 답변 컨텍스트 타입명 정리`
- `1761a62 refactor(server): 자료 업로드 관찰 리포터 분리`
- `db593d6 refactor(server): 자료 저장 관찰 경계 분리`
- `e6ec50d refactor(server): 검색 전략 흐름 분리`
- `fee5cf3 refactor(server): 답변 근거 투영 흐름 분리`
- `9413a16 refactor(server): 답변 payload 정규화 경계 분리`

## 확인한 파일

- `apps/server/api/routes/materials.py`
- `apps/server/api/routes/questions.py`
- `apps/server/use_cases/materials.py`
- `apps/server/use_cases/questions.py`
- `apps/server/materials/ingestion.py`
- `apps/server/materials/observation.py`
- `apps/server/materials/store.py`
- `apps/server/questions/observation.py`
- `apps/server/retrieval/models.py`
- `apps/server/retrieval/search.py`
- `apps/server/answers/library_chat.py`
- `apps/server/tests/test_material_upload_use_case.py`
- `apps/server/tests/test_question_use_case.py`
- `apps/server/tests/test_retrieval_search.py`
- `apps/server/tests/test_library_chat_answer.py`
- `apps/server/tests/test_materials_api.py`

## 남은 판단

- 후속 refactor 범위가 커지면 이 기준을 하위 spec으로 나누는 방식을 검토한다.
- compatibility alias인 `RetrievalCandidate = RetrievedSource`, `ContextPack = AnswerContext`를 언제 제거할지.
- observation record 구조가 더 커질 때 파일 분리 기준을 어느 정도 크기나 변경 위험에서 잡을지.
- retrieval/answer 모듈 분리는 지금 바로 할 일이 아니라, 다음 변경에서 읽기 흐름이 다시 흐려질 때 적용할 후보로 둘지.
