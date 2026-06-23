# Terminology authority boundary

작성일: 2026-06-15

상태: 용어 정합성 기준 spec. 2026-06-15 용어 계약 경계 정리 작업을 기준점으로 삼아, TripProof의 active 문서와 현재 code/API/schema에서 용어가 어느 층위와 권한으로 쓰이는지 정렬한다.

## 왜 지금

TripProof 문서와 서버 코드는 제품 언어, API 이름, RAG 내부 이름, 관측 산출물 이름, 과거 기록 이름을 함께 갖고 있다. 이 상태에서 같은 단어가 다른 층위에서 쓰이고, 다른 단어가 같은 개념처럼 보이면 다음 개발자는 문서를 읽을 때마다 다음을 추론해야 한다.

- 이 말은 현재 제품 기준어인가.
- 코드/API/schema 이름인가.
- RAG나 extraction 내부 후보인가.
- observation/export/eval 산출물인가.
- 과거 작업 기록에 남은 이름인가.
- 지금 따라야 할 기준인가, 당시 판단을 보존한 기록인가.

이번 정리의 목적은 모든 단어를 하나로 밀어붙이는 것이 아니다. 근거 없이 통일하지 않되, 근거가 흩어졌다는 이유로 판단을 미루지도 않는다. 각 용어가 어느 문서 권한과 처리 층위에 속하는지 밝혀서 개발자가 읽고 행동할 수 있게 한다.

관련 코드 흐름 기준은 [Server readable-flow refactor](../2026-06-15-server-readable-flow-refactor/)가 다룬다. 이 문서는 코드 흐름 자체가 아니라 그 흐름을 읽는 용어 권한과 해석 경계를 다룬다.

## 문제 본체

이 문제는 glossary가 부족한 문제가 아니다. 용어의 뜻보다 먼저, 그 용어가 어느 층위에서 어떤 판단 권한을 갖는지가 안 보이는 문제다.

예를 들어 `Artifact`, `Material`, `SourceUnit`은 모두 "자료"처럼 보이지만 같은 말이 아니다.

- `Artifact / 자료`는 사용자가 Library에 넣은 원본 자료를 말하는 제품 언어다.
- `Material`은 backend/API에서 업로드된 자료를 저장하고 처리하는 record다.
- `SourceUnit`은 Material 텍스트에서 파생된 retrieval/grounding 원문 단위다.

또 `FactCandidate`, `AICandidate`, `RetrievedSource`는 모두 후보처럼 보이지만 붙는 위치가 다르다.

- `AICandidate`는 제품 화면에서 AI가 제안하는 검토 전 후보다.
- `FactCandidate`는 extraction 내부 후보 재료다.
- `RetrievedSource`는 RAG가 answer composer에 넘길 검색 후보 source다.

따라서 해결 기준은 "중복 단어를 전부 제거한다"가 아니라, generic term이 나타날 때 lane을 드러내고, active 문서에서 현재 기준어와 과거 이름을 섞어 쓰지 않는 것이다.

## Goal

TripProof의 active 문서와 현재 code/API/schema에서 용어가 어느 층위와 권한으로 쓰이는지 명확히 정렬해서, 다음 개발자가 이 말이 제품 기준어인지, 코드 이름인지, RAG 내부 후보인지, 관측 산출물인지, 과거 기록인지를 추론하지 않아도 되게 만든다.

구체적으로는 다음 상태를 목표로 한다.

- 제품 문서는 `Artifact`, `Library`, `ChatAnswer`, `CardDraft`, `DashboardCard`, `FieldCard`, `EvidenceState` 같은 제품 기준어를 우선한다.
- API/code-facing 문서는 `Material`, `LibraryItem`, `EvidenceRef`, `SourceUnit`, `AnswerContext`, `RetrievedSource`처럼 현재 구현의 실제 이름을 쓴다.
- RAG/extraction 내부 후보는 사용자-facing 결과처럼 쓰지 않는다.
- observation/export/eval 산출물은 product object처럼 쓰지 않는다.
- active 문서에서는 과거 alias나 이전 이름을 preferred name처럼 유지하지 않는다.
- 과거 기록과 archive는 당시 판단의 증거로 보존하되, 현재 기준인 것처럼 재해석하지 않는다.

## Non-goals

- 과거 work-log, archive, raw notes를 현재 용어로 전부 소급 수정하지 않는다.
- 제품 언어를 전부 API 이름으로 바꾸지 않는다.
- 코드 타입명을 숨기기 위해 중요한 용어를 과하게 풀어쓰지 않는다.
- 이름만 바꿔 product behavior, retrieval quality, LLM quality가 개선됐다고 주장하지 않는다.
- 아직 구현되지 않은 product flow나 eval 결과를 완료된 것처럼 쓰지 않는다.
- 모든 용어를 한 glossary 파일로 강제 수렴시키지 않는다. 권한 지도와 lane map이 먼저다.

## 문서 권한 지도

| 문서/영역 | 권한 | 읽는 법 |
| --- | --- | --- |
| `docs/product-model.md` | 제품 언어, 상태 2축, chat-first 흐름 기준 | 제품 객체와 사용자-facing 상태를 볼 때 우선 참고한다. 구현 이름을 대체하지는 않는다. |
| `docs/prd.md` | 요구사항, AC, AI behavior 기준 | 제품 언어는 `product-model.md`를 따르고, 요구/실패 기준을 정리한다. |
| `docs/specs/README.md` | spec 운영 언어 기준 | feature, slice, AC, stub, 구현면 같은 spec 작성 용어의 기준이다. |
| active feature specs | 특정 product path의 판단 기준 | 부모 product/model 용어를 재정의하지 않고, 해당 slice에서 필요한 경계만 좁힌다. |
| server code/API/schema | 구현 계약 기준 | 실제 request/response, type, test contract에 가까운 이름을 따른다. 제품 설명과 다르면 lane을 명시한다. |
| observation/export/eval docs | runtime 관측과 산출물 기준 | product response가 아니라 product path를 관찰하는 기록임을 드러낸다. |
| roadmap/work-log/decisions/archive/raw notes | 과거 판단과 진행 기록 | 현재 기준으로 읽을 때는 active 기준과 구분한다. 필요한 경우 reference로만 남긴다. |

## Lane map

| Lane | 대표 용어 | 기준 |
| --- | --- | --- |
| Product language | `Artifact`, `Library`, `ChatAnswer`, `AICandidate`, `CardDraft`, `DashboardCard`, `FieldCard`, `EvidenceState`, `ReviewDecision` | 사용자가 이해하는 제품 흐름과 상태를 설명한다. |
| API / code-facing terminology | `Material`, `LibraryItem`, `QuestionResponse`, `EvidenceRef`, `SourceUnit`, `materialId`, `sourceUnitId` | request/response/schema/code contract를 설명한다. |
| RAG / answer-composer internal | `AnswerContext`, `RetrievedSource`, `SourceRetrievalTrace`, `EmbeddingRecord`, `NormalizedAnswerItemPayload` | retrieval 결과가 answer composer와 grounding으로 넘어가는 내부 경계를 설명한다. |
| Extraction / candidate lane | `FactCandidate`, `FactProposal`, `FactTarget` | 과거 정형 추출/후보 생성 재료 용어다. 현재는 코드 타입으로 존재하지 않으며 Library Chat 사용자-facing 기준어도 아니다. |
| Observation / export lane | `ObservationRecord`, `MaterialUploadObservationRecord`, `QuestionObservationRecord`, `ObservationExportEnvelope`, `trace`, `run`, `local observation artifact`, `eval run artifact` | product path 실행 조건과 관측 산출물을 설명한다. |
| Historical / reference lane | `ContextPack`, `RetrievalCandidate`, archive/raw/work-log의 이전 표현 | 과거 기록에 남은 이름이다. active 구현과 active 문서에서는 현재 이름을 쓴다. |

## 이번 작업에 반영된 결정

| 결정 | 이유 | 반영 위치 |
| --- | --- | --- |
| `ChatAnswer`를 현재 사용자/API-facing 답변 기준으로 둔다 | `/api/questions`가 반환하는 현재 사용자가 읽는 결과는 fact 후보 자체가 아니라 상태와 인라인 근거를 가진 답변이다 | `docs/prd.md`, `docs/product-model.md`, active specs |
| `FactCandidate`는 extraction 내부 후보로 좁힌다 | 후보 생성 재료를 제품 결과처럼 쓰면 답변, 카드 초안, 대시보드 카드의 사람 확인 경계가 흐려진다 | `docs/product-model.md`, `docs/prd.md`, accommodation specs |
| `EvidenceRef`는 현재 schema 필드 기준으로 설명한다 | 현재 구현은 `artifactId`가 아니라 `materialId`, `sourceUnitId`, `label`, `locator`, `snippet`으로 원문 근거를 가리킨다 | `docs/prd.md`, `docs/specs/2026-06-06-accommodation-checkin-agoda-fukuoka/03-evidence-backed-facts.md` |
| `AnswerContext` / `RetrievedSource`를 현재 retrieval 이름으로 둔다 | answer composer 입력 context와 검색 후보 source라는 층위가 드러난다 | `apps/server/retrieval/models.py`, `docs/product-model.md`, server readable-flow spec |
| `ContextPack` / `RetrievalCandidate` alias를 제거한다 | 과거 이름이 남아 있으면 현재 preferred name이 둘처럼 보인다 | `apps/server/retrieval/models.py` |
| `FactCandidateResponse`와 `ChatAnswerItemResponse.from_fact`를 제거한다 | 현재 API 응답 경계에서 쓰지 않는 helper가 FactCandidate를 사용자-facing response처럼 보이게 한다 | `apps/server/schemas/evidence.py`, `apps/server/schemas/answers.py` |
| active 문서의 `TripFact` 표현을 `ChatAnswer` 계약으로 바꾼다 | `TripFact`가 현재 product/API 기준어처럼 보이면 실제 흐름과 어긋난다 | specs example, PRD domain contract |
| accommodation active spec의 흐름은 `SourceUnit -> RetrievedSource/AnswerContext -> ChatAnswer/EvidenceRef`로 읽는다 | 01-04가 같은 제품 path를 설명하므로, source/evidence/candidate 같은 일반어보다 현재 lane 이름을 드러내야 한다 | accommodation specs |
| observation/export/eval 산출물은 제품 `Artifact`와 구분한다 | bare `local artifact`, `eval artifact`, `Artifact shape`는 제품 원본 자료인 `Artifact / 자료`와 섞여 읽힐 수 있다 | question runtime recording specs |
| `candidate_summary`는 retrieval 후보 요약으로 쓴다 | `candidate_summary`는 extraction 후보(FactCandidate)가 아니라 `AnswerContext.candidates`의 count/score-presence 요약이다 | `03-question-observation.md`, `06-langsmith-observation-adapter.md` |

## 용어 작성 기준

중요한 용어는 없애거나 전부 풀어쓰지 않는다. 처음 등장할 때 역할과 lane을 짧게 붙이고, 이후에는 정확한 용어를 유지한다.

| 상황 | 작성 기준 |
| --- | --- |
| 제품 문서에서 처음 등장 | `자료(Artifact)`, `답변(ChatAnswer)`처럼 한국어 역할어와 canonical term을 함께 둔다. 이후에는 문맥에 맞게 하나를 유지한다. |
| API/schema 문서에서 처음 등장 | `Material`: 업로드된 자료를 저장·처리하는 backend record처럼 type name을 먼저 두고 역할을 짧게 설명한다. |
| RAG/AI 내부 문서에서 후보를 말할 때 | bare `candidate`를 피하고 `retrieval 후보(RetrievedSource)`, `extraction 후보(FactCandidate)`, `제품 제안(AICandidate)`처럼 qualifier를 붙인다. |
| source를 말할 때 | bare `source`만 쓰지 말고 `SourceUnit 원문`, `EvidenceRef`, `companion source`, `source unit 후보`처럼 어느 lane인지 밝힌다. |
| artifact를 말할 때 | 제품 원본은 `Artifact / 자료`, observation export 산출물은 `local observation artifact`, eval 산출물은 `eval run artifact`처럼 쓴다. |
| 과거 이름을 언급할 때 | 현재 preferred name처럼 쓰지 않고, "과거 기록에 남은 이전 이름"이라고 밝힌다. |
| 상태 문구를 말할 때 | `근거 있음`, `확인 필요`, `근거 부족`, `자료 충돌`, `직접 확인`, `현장 저장`은 사용자-facing 문구로 쓰고, 필요한 경우 `EvidenceState`나 `ReviewDecision` 축을 붙인다. |

과하게 풀어쓴 냄새는 용어가 사라져 같은 개념을 검색하기 어려운 상태다. 반대로 덜 설명한 냄새는 `candidate`, `source`, `context`, `artifact`, `state` 같은 일반 단어만 남아 독자가 층위를 다시 추론해야 하는 상태다.

## Acceptance criteria

1. active product 문서에서 원본 자료를 설명할 때 `Artifact / 자료`를 우선하고, backend record를 말할 때만 `Material`을 쓴다.
2. active API/schema 문서에서 `EvidenceRef`는 현재 구현 필드인 `materialId`, `sourceUnitId`, `label`, `locator`, `snippet` 기준으로 설명한다.
3. 현재 Library Chat의 사용자-facing 출력은 `ChatAnswer`로 설명하고, `FactCandidate`는 extraction 내부 후보로만 쓴다.
4. active code와 active 문서에서 `AnswerContext` / `RetrievedSource`를 현재 이름으로 쓰고, `ContextPack` / `RetrievalCandidate`를 preferred alias처럼 남기지 않는다.
5. observation/export/eval 용어는 product object처럼 쓰지 않는다. `run artifact`는 제품 `Artifact`와 구분한다.
6. `candidate`, `source`, `context`, `artifact`, `state`처럼 여러 lane에서 쓰이는 일반어는 처음 등장하거나 혼동 가능성이 있을 때 qualifier를 붙인다.
7. 과거 기록은 현재 기준으로 소급 정리하지 않되, active 문서가 과거 표현을 현재 기준처럼 반복하면 고친다.
8. 용어 정리 때문에 `/api/materials`, `/api/questions` response body contract를 바꾸지 않는다.

## 확인한 커밋

- `b12b8a1 refactor(server): 용어 계약 경계 정리`
- `2bee368 docs(specs): 숙소 체크인 용어 lane 정렬`
- `9065a46 docs(specs): observation 용어 lane 보정`

이 커밋들은 다음을 포함한다.

- `ChatAnswer`와 `FactCandidate`의 사용자/API 경계 정리.
- `AnswerContext` / `RetrievedSource`를 현재 retrieval 용어로 확정.
- 사용하지 않는 compatibility alias와 response helper 제거.
- active 문서의 `EvidenceRef`, `FactCandidate`, retrieval 용어 설명을 현재 code/schema 기준에 맞춤.
- accommodation active spec의 `SourceUnit`, `RetrievedSource`, `AnswerContext`, `ChatAnswer`, `EvidenceRef` lane 정렬.
- question runtime recording specs의 `candidate_summary`, `local observation artifact`, `eval run artifact` 표현 보정.

## 확인한 파일

- `docs/product-model.md`
- `docs/prd.md`
- `docs/specs/2026-06-06-accommodation-checkin-agoda-fukuoka/01-file-parsing.md`
- `docs/specs/2026-06-06-accommodation-checkin-agoda-fukuoka/index.md`
- `docs/specs/2026-06-06-accommodation-checkin-agoda-fukuoka/02-source-units-retrieval.md`
- `docs/specs/2026-06-06-accommodation-checkin-agoda-fukuoka/03-evidence-backed-facts.md`
- `docs/specs/2026-06-06-accommodation-checkin-agoda-fukuoka/04-library-chat-evidence.md`
- `docs/specs/2026-06-10-question-runtime-recording/index.md`
- `docs/specs/2026-06-10-question-runtime-recording/02-material-upload-observation.md`
- `docs/specs/2026-06-10-question-runtime-recording/03-question-observation.md`
- `docs/specs/2026-06-10-question-runtime-recording/04-runtime-config-snapshot.md`
- `docs/specs/2026-06-10-question-runtime-recording/05-observation-export-boundary.md`
- `docs/specs/2026-06-10-question-runtime-recording/06-langsmith-observation-adapter.md`
- `docs/specs/2026-06-10-question-runtime-recording/07-observation-correlation-id.md`
- `docs/specs/2026-06-10-question-runtime-recording/08-eval-run-correlation-artifact.md`
- `docs/specs/2026-06-15-server-readable-flow-refactor/index.md`
- `docs/specs/examples/example-large-feature-checkin-slice-build.md`
- `apps/server/retrieval/models.py`
- `apps/server/schemas/answers.py`
- `apps/server/schemas/evidence.py`

## 남은 판단

- `AICandidate`와 `FactCandidate`가 같은 "후보"로 읽히는 문제는 계속 조심해야 한다. 제품 제안인지, extraction 내부 후보인지, retrieval 후보인지 문맥에서 바로 보여야 한다.
- `Evidence`와 `EvidenceRef`의 관계는 제품 설명과 API schema에서 밀도가 달라질 수 있다. 제품 문서에서는 원문 근거의 역할을 말하고, API/schema에서는 참조 필드를 말한다.
- observation model이 더 커지면 `ObservationRecord`, `trace`, `run`, `artifact`의 작성 기준을 별도 문서나 server observation spec에 더 좁혀둘지 검토한다.
- 용어를 풀어쓰는 밀도는 계속 조정 대상이다. 중요한 타입명을 숨기지 않으면서 첫 등장에는 역할과 lane을 짧게 붙이는 방식을 기본으로 둔다.
