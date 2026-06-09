# 작업 로그

나중 결정에 영향을 주는 작업만 짧게 남긴다. 이 파일은 과거 기록이지 다음 작업 queue가 아니다. 구현 중 반복해서 다시 볼 오해, drift, 경계 관찰은 `docs/implementation-notes/`에 따로 둔다. 공개 문서 독립성을 해칠 수 있는 표현은 별도 점검한다.

## 2026-05-28 - 초기 구조 정리

- 바뀐 것: README, product/eval/fixture/docs 디렉토리, spec/decision/work-log/eval run 자리를 추가했다.
- 남은 관찰: 자료를 넣고 결과를 확인할 수 있는 가장 작은 product path가 아직 필요하다.

## 2026-05-30 - preview UX 통합 / chat-first 채택 / 상태 2축

- 바뀐 것: chat-first preview(`docs/archive/preview/prd.md` + `docs/archive/preview/tripproof-preview-c.html`)를 제품 1차 경험으로 채택했다. `docs/product-model.md` 통합 모델 기준 문서를 신설하고, moment-first 입구와 "채팅=Later Feature" 프레이밍을 버렸다. 상태를 근거 축(EvidenceState)과 결정 축(ReviewDecision·카드 출처) 2축으로 분리해 "확인 필요"(needs_review)와 "직접 확인"(user 카드 출처)의 어휘 과부하를 풀었다. acceptance·AI Must Not·도메인 타입 이름·eval 축은 보존했다. 자세한 근거는 `docs/decisions/2026-05-30-preview-integration-chat-first.md`.
- 남은 관찰: 코드 드리프트(drift, 코드와 문서가 벌어진 지점)는 문서만으로 닫지 않고 구현 slice에서 판단한다. 후보는 `TripFact.confidence: number`의 UI 노출 여부와 필드 존치, `TripFact.value`의 `string | null` 확장, 결정 축(ReviewDecision/카드 출처)과 `category` 축의 공유 타입 승격이다.

## 2026-05-30 - 1차 로드맵·MVP 계획 문서 신설 (느슨한 초안 · 폴더 버전화)

- 바뀐 것: 1차 로드맵 `docs/roadmap/v1.md`를 신설했다. 고정 계획이 아니라 갈아엎을 수 있는 초안이라 `docs/roadmap/` 폴더에 버전 파일로 쌓기로 했다(현재 `v1.md`, 이후 `v2.md`로 추가하고 폴더 README의 '현재 기준'을 갱신). 코드를 분석해 현재 상태(실행 세팅 없음, client는 옛 moment-first 데모, server ai 미연결, 데이터 2벌)를 출발점으로 적고, 구조 정비(AI를 `src/server/ai`→`src/ai`로 상위화 + 최소 실행 세팅, 권장: 단일 패키지+경계 별칭) → MVP가 통과시킬 한 흐름(숙소 체크인 흐름이 실제 `shared` 계약을 통해 끝까지 돔) → 확장 후보 목록을 느슨한 메뉴로 정리했다. 다른 세션이 단독으로 작업을 고를 수 있게 일정·강한 단계는 두지 않았다.
- 남은 관찰: 구조 정비를 실제로 하면 `decisions/`에 결정 노트를 남기고 현재 docs 색인을 맞춘다(AI 위치 베이스라인 변경). 관련 MVP 판단은 현재 코드 상태와 사용자 요청에서 다시 닫는다.

## 2026-06-03 - React client 골격과 Python AI 후보 생성 경계

- 바뀐 것: 최신 LTS Node 기준 `.nvmrc`와 Vite/React 실행 세팅을 추가했고, active client를 React 앱으로 전환했다. 기존 preview를 버리지 않고 상단/자료함/확인/대시보드/현장/원문 근거 표의 구조를 살리되, confidence bar와 넓은 moment-first 목업 세계는 새 화면 중심에서 제외했다. Python AI는 `src/ai/`에 후보 생성 baseline과 prompt/provider 자리를 두고, TS `src/server/trip-facts`가 후보를 `src/shared/tripFacts.ts`의 product contract로 정규화하는 경계를 택했다. 관련 결정 근거는 `docs/decisions/2026-06-03-react-client-python-ai-boundary.md`.
- 남은 관찰: client sample은 `src/client/data/tripSession.ts`에 typed session data로 남겼다. server stub/adapter가 붙으면 client 밖으로 옮기거나 제거한다. 다음 구현 판단은 Python 후보 JSON을 TS server entry에 연결할지, 먼저 client sample을 더 줄일지에서 다시 닫는다.

## 2026-06-03 - client Tailwind 컴포넌트화 / app.js 잔재 제거

- 바뀐 것: active client entry를 `src/client/App.tsx`로 정리하고, 상단바·자료함 rail·확인 채팅·카드 초안·후보 rail·대시보드·현장 카드를 `src/client/components/`로 분리했다. Tailwind v4 Vite plugin과 CSS entry를 연결했고, 기존 대형 `styles.css`는 Tailwind import와 최소 base만 남겼다. 연결되지 않던 vanilla DOM `src/client/app.js`, 단일 파일 `TripProofApp.tsx`, mock 이름의 `demoTrip.ts`는 제거했다.
- 남은 관찰: Vite build와 주요 viewport screenshot으로 레이아웃을 확인했다. Node 버전 경고는 별도 환경 정리 항목으로 남았다.

## 2026-06-08 - Agoda PDF 01 backend ingest / uv 전환

- 바뀐 것: Python backend를 root `server/`로 두고 `uv`/`uv.lock` 기준으로 전환했다. `/api/materials`는 PDF를 받아 `pypdf`로 텍스트와 page count를 추출해 in-memory material로 저장하고, `/api/questions`는 ready material의 파싱 본문을 질문 context로 받는다. client는 PDF 선택/업로드/status 표시와 질문 API 호출을 맡는다. 기존 `src/ai`, `src/server/trip-facts`, `src/shared`는 호환층으로 남기지 않고 삭제했다. 관련 결정은 `docs/decisions/2026-06-08-python-backend-uv-ingest-boundary.md`.
- 남은 관찰: 01은 답변 생성이 아니라 파싱 본문이 질문 입력으로 들어가는 데까지만 닫았다. 02에서 evidence state, 후보 생성, 민감정보 guard를 Python backend schema로 새로 잡아야 한다.

## 2026-06-08 - root client/server 구조와 backend 확장 골격

- 바뀐 것: 실행 단위 기준에 맞춰 React app을 root `client/`로 옮겼고, Python backend를 `api`, `core`, `schemas`, `materials`, `retrieval`, `extraction`, `llm`, `cards` 축으로 나눴다. `retrieval`에는 chunk/search 골격을 두고, 질문 API의 excerpt 선택을 retrieval helper로 옮겼다. `extraction`은 제품 판단, `llm`은 provider 호출 인프라로 분리했다.
- 남은 관찰: 실제 LLM provider와 extraction 구현은 아직 열지 않았다. 다음 제품 slice에서 `apps/server/extraction/checkin.py`가 parsed material text를 받아 evidence-backed 후보를 만들도록 닫는다.

## 2026-06-08 - apps runtime 구조로 client/server 묶음

- 바뀐 것: root에 떨어져 있던 `client/`, `server/`를 `apps/client/`, `apps/server/`로 묶었다. Python import package 이름은 `server.*`를 유지하고, 실행과 테스트에서 `PYTHONPATH=apps`로 위치를 연결한다.
- 남은 관찰: `apps/`는 실행 단위 묶음이고, `eval/`, `fixtures/`, `docs/`는 product를 관찰하거나 설명하는 바깥 레이어로 root에 남긴다.

## 2026-06-09 - 02 source unit / embedding boundary

- 바뀐 것: ready material 생성 시 `[page N]` 마커를 page locator가 있는 `SourceUnit`으로 나누고, 각 source unit에 pending `EmbeddingRecord`를 붙인다. `IndexRecord`는 두지 않고 lexical 검색용 text는 `SourceUnit.searchText`로 둔다. local Ollama profile(`nomic-embed-text-v2-moe`, 768 dimensions)은 기본값으로 잡되, 실제 vector 생성은 `TRIPPROOF_EMBEDDING_AUTO_GENERATE=1`일 때만 수행한다. 질문 API의 최소 확인 경로는 `excerpt`, `excerptLocator`, `excerptSourceUnitId`를 반환한다.
- 남은 관찰: Supabase adapter/schema, stable source unit id, 실제 Ollama 호출 검증, 03의 `RetrievalCandidate`/`EvidenceRef`/`TripFact` 경계를 다음에 닫아야 한다. 02 검색 결과는 accepted evidence가 아니다.

## 2026-06-09 - 03 스펙 구현 참조 맥락 drift 관찰

- 바뀐 것: `03-evidence-backed-facts.md` 구현 중 하위 스펙만 보고 parent feature spec과 02/04 계약을 잃으면 `target -> retrieval candidate -> SourceUnit grounding -> TripFact` 경로가 특정 PDF 문장/값 중심 구현으로 좁아질 수 있음을 확인했다. 스펙 구현 전 참조 맥락 확인 기준을 문서에 추가했다.
- 남은 관찰: 다음 03/04 작업에서 입력이 앞 단계 product artifact인지, 출력이 뒤 단계 contract인지, deterministic/stub이 같은 계약을 통과시키는 test double인지 관찰한다. 이 기록은 작업 queue가 아니며, 아직 채택/기각한 방법론 결정은 아니므로 decision note는 만들지 않는다.

## 2026-06-09 - Supabase vector retrieval backend 연결

- 바뀐 것: `RetrievalRepository`에 vector match 계약을 추가하고, Supabase REST adapter와 pgvector migration을 붙였다. product 실행은 `TRIPPROOF_RETRIEVAL_BACKEND=supabase`일 때 `tripproof_source_units` / `tripproof_source_embeddings`를 저장하고 `match_tripproof_source_units` RPC로 후보 source unit을 가져온다. `.env.example`은 Supabase backend 기준으로 정리하되 실제 URL과 service role key는 비워 둔다.
- 당시 남은 관찰: Supabase 연결과 migration은 확인됐지만, 설치된 Ollama embedding model과 `.env`의 model 이름이 아직 맞지 않아 실제 업로드→ready vector→RAG 응답 관찰은 다음 단계로 남았다. check-in fact proposer는 아직 local proposer 기반이었고, LLM proposer 전환은 별도 03 slice로 남았다.

## 2026-06-09 - 03 LLM fact proposer product route 연결

- 바뀐 것: check-in fact proposer의 product 기본 경로를 local proposer에서 Ollama JSON proposer로 전환했다. 질문 API는 Supabase vector retrieval로 만든 `ContextPack`을 proposer에 넘기고, validator는 source unit 원문으로 grounding된 proposal만 `supported`로 받아들인다. 해당 시점의 실행 관찰에서는 업로드된 예약 PDF가 source unit과 vector retrieval을 거쳐 check-in fact proposer에 전달되고, 예약 확정서 제시는 `supported`, 체크인 시작 시각은 날짜 오인 없이 `missing`으로 남는 흐름을 확인했다.
- 후속 정리: 민감정보 감지, PDF 공백 정리, retrieval query tokenization, page marker parsing을 문자열/token 기반 처리로 바꿔 서버 active 경로의 코드 내부 패턴 매칭 잔재를 줄였다.
- 남은 관찰: Ollama proposer 실패는 현재 `missing`으로 낮춘다. retry/backoff, provider 오류의 사용자-facing 상태, LLM이 맞는 source unit을 골랐지만 snippet을 의역하는 경우의 evidence fallback 범위는 다음 03/04 경계에서 다시 판단한다.

## 2026-06-09 - spec-driven skill / README 축약 기록

- 바뀐 것: `.claude/skills/spec-driven/SKILL.md`를 runtime core로 줄이고, 자세한 읽기 순서와 calibration은 `docs/specs/README.md`가 소유하도록 정리했다. 배경, 보존한 guardrail, 복구 기준은 `docs/implementation-notes/2026-06-09-spec-driven-skill-readme-refactor/`에 남겼다.
- 남은 관찰: 이 개편이 실제 작업에서 제품 흐름 손실, fixture/seed 값 맞추기, raw output을 product result로 보는 drift, 또는 새로운 gate화를 만들면 먼저 작업 전 기준(`6adc709`)의 skill / README 복구를 검토한다.
