# 자료와 질문 실행 조건의 Runtime Observation Record

작성일: 2026-06-10

상태: 작업 spec. 자료 업로드와 자료함 질문 응답 경로를 prompt/config snapshot과 내부 observation record로 다시 확인 가능하게 만들고, LangSmith는 그 record의 선택적 export 계층으로 둔다.

## 왜 지금

TripProof는 사용자가 자료를 넣고 자료함에 질문해 근거가 붙은 답변을 받는 제품 경로를 갖기 시작했다. 다음 문제는 자료 업로드와 질문 답변이 흔들렸을 때 어떤 파일 처리 결과, prompt, provider, retrieval 설정, source 후보로 그 결과가 만들어졌는지 나중에 확인하기 어렵다는 점이다.

이번 작업은 LangSmith를 product 성공 기준으로 올리는 일이 아니다. `/api/materials`와 `/api/questions`의 product 응답 계약은 유지하고, 개발자가 같은 사용자 장면을 다시 확인할 때 실행 조건과 관찰 기록을 복원할 수 있게 한다.

관측 순서는 외부 trace provider보다 product runtime의 내부 record가 먼저다. material upload, config/prompt snapshot, question answer 경계에서 무엇을 관찰할지 정한 뒤, LangSmith adapter는 그 record를 내보내는 출력 계층으로 붙인다.

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
- 이 관찰 정보가 사용자-facing 자료 상태나 답변에 raw debug로 섞이지 않았는가.

## Goal

- active Library Chat prompt가 코드 본문 문자열이 아니라 이름, 버전, 본문 hash를 가진 prompt document로 분리된다.
- `/api/materials`와 `/api/questions` 경로에서 실행된 config와 prompt snapshot을 같은 원천에서 만들 수 있다.
- 내부 observation/snapshot record는 product 경로 옆에서 생성되며, product code가 eval run artifact나 fixture에 의존하지 않는다.
- LangSmith trace는 내부 record가 생긴 뒤 붙는 선택적 export adapter다.
- 기본 material/question 응답 계약은 유지하고, raw retrieval/debug 정보는 사용자-facing 응답으로 노출하지 않는다.

## Rules

- `/api/materials`의 제품 흐름은 `upload -> parse -> source unit/embedding records -> ready/failed material -> 화면`이다. 내부 observation/snapshot record는 이 흐름을 관찰한다.
- `/api/questions`의 제품 흐름은 `ready material -> retrieval -> answer composer -> grounded ChatAnswer -> 화면`이다. 내부 observation/snapshot record는 이 흐름을 관찰한다.
- 내부 observation record가 먼저이고 LangSmith trace는 그 record를 외부로 내보내는 adapter다.
- prompt version/hash는 실행에 쓰인 prompt document에서 나온다. 기록용 값과 실행용 값이 따로 존재하면 안 된다.
- config snapshot은 provider/model/retrieval knob처럼 material/question 결과를 바꿀 수 있는 값만 먼저 담는다.
- LangSmith export가 비활성화되어도 material upload와 question answer의 응답 계약은 동일하게 동작해야 한다.
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
| 02 | [Material upload 관측 record](02-material-upload-observation.md) | `POST /api/materials`의 upload, parse, source unit/embedding record 생성, ready/failed 경계를 내부 observation record로 남기는 기준을 정한다 |

## 현재 코드에서 볼 곳

- `apps/server/api/routes/materials.py`: `/api/materials`가 upload, PDF parse, ready/failed material 생성을 연결한다.
- `apps/server/api/routes/questions.py`: `/api/questions`가 ready material, retrieval, `ChatAnswer`를 연결한다.
- `apps/server/materials/store.py`: ready material에서 source unit과 embedding record를 만든다.
- `apps/server/answers/library_chat.py`: Library Chat answer composer가 prompt renderer를 사용한다.
- `apps/server/prompts/README.md`: prompt document/runtime/renderer 책임 경계를 설명한다.
- `apps/server/prompts/assets/answer/library_chat_answer/2026-06-10.md`: 현재 active Library Chat prompt document다.
- `apps/server/prompts/runtime/prompt_document.py`: prompt markdown의 metadata, body, hash를 읽는 공통 runtime이다.
- `apps/server/prompts/runtime/prompt_store.py`: `assets/{domain}/{name}/{version}.md` 경로를 해석한다.
- `apps/server/prompts/renderers/answer/library_chat_answer.py`: Library Chat prompt body를 provider 입력으로 렌더한다.
- `apps/server/core/config.py`: provider, embedding, retrieval 설정의 현재 원천이다.
- `apps/server/llm/ollama.py`: provider call 경계다.
- `eval/README.md`, `eval/runs/README.md`: eval은 product behavior 관찰자라는 기록 경계다.

## 구현면 펼치기

| 구현 요소 | 이번 장면에서 필요한 이유 | 현재 코드/문서 비교 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Material ingest observation | 질문 결과가 어떤 material 처리 결과에서 나왔는지 추적해야 한다 | `/api/materials`는 parse와 `store.add_ready`를 호출하지만 내부 관측 record는 없다 | material upload, parse success/failure, source unit/embedding record 생성, ready/failed 경계를 내부 record로 남긴다 |
| Runtime config snapshot | provider/model/retrieval knob이 자료 처리와 답변을 바꾼다 | `core/config.py`에 flat env constants가 있다 | material/question 실행에 영향을 주는 값만 snapshot으로 만든다 |
| Prompt snapshot | prompt 변경과 답변 변경을 연결해야 한다 | prompt document runtime은 prompt identity를 만들 수 있지만 question 실행 snapshot과 아직 연결되지 않았다 | prompt domain/name/version/body hash를 실행 기록에 연결한다 |
| Question path observation | 답변 흔들림을 retrieval/compose 경계에서 봐야 한다 | `/api/questions`는 product response만 반환한다 | 내부 관찰 record는 만들되 기본 response에는 raw debug를 섞지 않는다 |
| LangSmith export | 로컬 record만으로는 요청 단위 tree와 latency를 보기 어렵다 | 현재 dependency와 trace wrapper가 없다 | 내부 observation/snapshot record를 LangSmith로 내보내고, 꺼진 환경에서는 no-op로 통과한다 |
| Eval run record | 제품 동작을 반복 관찰해야 한다 | `eval/runs`는 placeholder 원칙만 있다 | product entry point, config snapshot, observed answer, failure, next verification point를 남길 수 있게 한다 |

## 먼저 고를 slice

첫 번째 slice는 Library Chat prompt document/runtime 분리다.

권장되는 다음 구현 단위는 `02-material-upload-observation.md`의 material observation record producer다.

그 다음 구현 단위는 `/api/questions`의 question execution record와 runtime config/prompt snapshot producer이며, LangSmith adapter는 이 record들이 생긴 뒤 optional export sink로 연결한다.

이 slice는 product answer를 바꾸는 작업이 아니라, 같은 product result가 어떤 조건에서 만들어졌는지 복원 가능하게 만드는 작업이다. 자료 상태나 답변이 바뀌면 그 변화는 material parsing/source unit 생성 때문인지, prompt/config 변경 때문인지, retrieval 후보 변경 때문인지 관찰할 수 있어야 한다.

## 이번 AC

1. `POST /api/materials`는 upload, parse, source unit/embedding record 생성, ready/failed 경계를 내부 observation record로 남길 수 있다.
2. active Library Chat prompt는 이름과 버전을 가진 document에서 로드되고, answer composer는 그 document를 사용한다.
3. material/question 실행에서 provider/model/retrieval/prompt version을 포함한 snapshot을 만들 수 있다.
4. LangSmith export는 내부 observation/snapshot record를 외부 trace로 내보내는 adapter이며, 꺼져 있어도 기존 material/question 응답 계약은 유지되고 raw debug나 eval 기록을 포함하지 않는다.

## 확인 방법

1. 기존 숙소 체크인 자료 장면에서 `/api/materials`로 PDF를 업로드한다.
2. 자료가 기존처럼 ready/failed material 응답 계약을 지키는지 확인한다.
3. `/api/questions`를 호출해 답변의 `근거 있음`/`근거 부족` 동작이 기존 기준과 동일한지 확인한다.
4. material/question 실행의 내부 observation/snapshot record가 raw payload 없이 만들어지는지 확인한다.
5. LangSmith가 켜진 환경에서 내부 record가 material/question trace로 export되는지 확인한다.
6. LangSmith가 꺼진 환경에서도 같은 product path가 동작하는지 확인한다.
7. 응답 payload가 raw retrieval candidate, raw LLM JSON, eval score를 사용자-facing answer처럼 포함하지 않는지 확인한다.

## 남은 판단

- snapshot을 API 응답의 개발자 전용 필드로 둘지, 별도 local run artifact로만 둘지.
- prompt snapshot을 version/hash만 둘지, 제한된 preview나 요약까지 둘지.
- material trace에서 embedding vector 자체를 제외하고 어떤 summary만 남길지.
- LangSmith trace metadata에 source unit 후보의 text를 남길지, id/count/score summary만 남길지.
- `eval/runs`의 첫 artifact를 수동 기록으로 시작할지, 작은 runner로 시작할지.
