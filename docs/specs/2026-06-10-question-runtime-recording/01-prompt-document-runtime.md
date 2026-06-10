# Prompt document runtime과 Library Chat renderer

작성일: 2026-06-10

상태: 하위 작업 spec. Library Chat prompt를 코드 문자열에서 versioned prompt document와 renderer로 분리한 기준을 기록한다.

## 왜 지금

`/api/questions` 답변이 흔들릴 때 나중에 비교하려면 어떤 실행 prompt가 쓰였는지 이름, 버전, hash로 확인할 수 있어야 한다. 동시에 prompt는 answer, retrieval, rerank, judge, extraction처럼 계속 늘어날 수 있으므로 공통 loader가 `System`, `User`, rubric, JSON schema 같은 body 의미를 고정하면 안 된다.

이번 하위 spec은 LangSmith 연결 자체가 아니라, LangSmith와 config snapshot이 나중에 참조할 수 있는 prompt identity를 먼저 만든다.

## 사용자 장면

사용자가 자료함에 질문한다. answer composer는 Library Chat prompt document를 읽어 provider 입력으로 렌더하지만, 사용자-facing 답변에는 prompt metadata, 원문, raw payload를 섞지 않는다.

## Goal

- Library Chat 실행 prompt는 `apps/server/prompts/assets/answer/library_chat_answer/{version}.md`에 둔다.
- 공통 runtime은 metadata, title, body, file hash, body hash, asset path만 읽고 prompt body 의미를 해석하지 않는다.
- Library Chat renderer만 `System`/`User` section과 placeholder를 해석한다.
- 한글 전체 번역은 markdown comment metadata 안에 두고 provider 입력으로 넘기지 않는다.
- `apps/server/answers/library_chat.py`는 renderer를 통해 prompt를 사용한다.

## Rules

- 공통 runtime은 `System`, `User`, rerank, judge rubric, JSON output 같은 prompt family별 의미를 모른다.
- prompt document의 metadata, title, `translation_ko`는 provider 입력에 섞지 않는다.
- renderer가 고른 실행 body 일부만 provider 입력이 된다.
- snapshot과 trace에 남길 prompt identity는 prompt 전문이 아니라 `domain`, `name`, `version`, `fileHash`, `bodyHash`, repo-relative `assetPath`다.
- prompt 내용 변경은 새 version file 추가를 기본으로 한다.
- `translation_ko`는 사람이 원문을 바로 이해하기 위한 보조 정보이므로 원문이 바뀌면 함께 갱신한다.

## 설계 판단

- prompt document는 LLM provider 형식이 아니라 실행 prompt를 보관하는 문서다. provider별 message shape는 renderer나 composer가 책임진다.
- markdown body의 section 이름과 placeholder 규칙은 prompt family마다 달라질 수 있다. 공통 runtime이 markdown을 의미 단위로 해석하지 않아야 rerank, judge, extraction prompt가 추가되어도 확장된다.
- 한글 번역은 원문 prompt를 사람이 바로 검토하기 위한 자료다. 제목을 한영 병기하거나 실행 body에 번역을 섞지 않고, comment metadata 안에 둔다.
- prompt 관련 파일은 `answers` 하위가 아니라 `server.prompts` 하위에 둔다. answer 외에 retrieval, rerank, judge, extraction에서도 같은 document/runtime 규칙을 쓸 수 있어야 한다.
- 새 prompt family가 생기면 공통 runtime을 넓히기보다 해당 family의 renderer와 tests를 추가한다.

## Non-goals

- LangSmith adapter나 trace 연결은 이 문서의 범위가 아니다.
- prompt admin UI, DB registry, provider별 prompt registry는 만들지 않는다.
- rerank, judge, extraction prompt를 새로 구현하지 않는다.
- config snapshot 전체 구조를 확정하지 않는다.
- prompt 전문 장기 저장 정책은 정하지 않는다.

## 현재 코드에서 볼 곳

- `apps/server/prompts/README.md`: prompt document, runtime, renderer의 책임 경계를 설명한다.
- `apps/server/prompts/assets/answer/library_chat_answer/2026-06-10.md`: 현재 active Library Chat prompt document다.
- `apps/server/prompts/runtime/prompt_document.py`: markdown metadata, title, body, hash를 읽는 공통 runtime이다.
- `apps/server/prompts/runtime/prompt_store.py`: `assets/{domain}/{name}/{version}.md` 경로를 해석한다.
- `apps/server/prompts/renderers/answer/library_chat_answer.py`: Library Chat prompt body를 provider 입력으로 렌더한다.
- `apps/server/answers/library_chat.py`: answer composer가 renderer를 통해 prompt를 사용한다.

## 구현면 펼치기

| 구현 요소 | 필요한 이유 | 현재 코드/문서 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Prompt document storage | prompt를 코드 문자열이 아니라 versioned document로 식별해야 한다 | `assets/answer/library_chat_answer/2026-06-10.md` | domain/name/version/display_name_ko/description_ko/translation_ko가 있는 markdown document가 있다 |
| Prompt document runtime | 여러 prompt family가 같은 방식으로 파일 identity를 얻어야 한다 | `runtime/prompt_document.py` | metadata/title/body/fileHash/bodyHash를 읽되 body 의미는 해석하지 않는다 |
| Prompt store | prompt 위치 규칙을 코드 곳곳에 흩뜨리지 않는다 | `runtime/prompt_store.py` | `assets/{domain}/{name}/{version}.md`를 한 곳에서 해석한다 |
| Library Chat renderer | answer prompt만의 section과 placeholder 의미를 담당해야 한다 | `renderers/answer/library_chat_answer.py` | renderer가 `System`/`User` section을 추출하고 question/source blocks를 렌더한다 |
| Answer composer wiring | 기존 product answer 경로가 새 prompt document를 써야 한다 | `answers/library_chat.py` | composer가 renderer를 사용하고 기존 `ChatAnswer` 동작을 유지한다 |
| Tests | 변경이 prompt identity와 product answer 경로를 깨지 않아야 한다 | `apps/server/tests` | metadata, hash, asset path, provider 입력 비노출, answer 동작을 확인한다 |

## 이번 AC

1. `OllamaLibraryChatAnswerComposer`는 `server.prompts.renderers.answer.library_chat_answer`를 통해 Library Chat prompt를 로드한다.
2. Prompt runtime은 `domain`, `name`, `version`, `bodyHash`, repo-relative `assetPath`를 prompt 전문 없이 제공할 수 있다.
3. 한글 제목과 전체 번역은 metadata comment block 안에 있고 provider system/user input에 나타나지 않는다.
4. 기존 Library Chat answer behavior는 유지된다.

## 확인 방법

1. `uv run pytest apps/server/tests/test_library_chat_answer.py apps/server/tests/test_materials_api.py`
2. `uv run pytest apps/server/tests`
3. `rg "answers\\.prompts|apps/server/answers/prompts|server\\.answers\\.prompts|prompts/loaders|markdown_prompt_asset|llm_prompt_file_loader" apps/server`가 비어 있는지 확인한다.

## 남은 판단

- prompt snapshot을 LangSmith metadata에 어느 깊이까지 남길지.
- prompt 전문을 저장하지 않는 원칙을 장기 로그 정책에서도 유지할지.
- rerank, judge prompt가 들어올 때 renderer 이름과 domain 분류를 어디까지 세분화할지.
