# 작업 로그

나중 결정에 영향을 주는 작업만 짧게 남긴다. 이 파일은 과거 기록이지 다음 작업 queue가 아니다.

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
- 남은 관찰: in-app Browser backend는 비어 있어 자동 클릭 검증은 대체 수단으로만 시도했다. Vite build와 데스크톱/모바일 Playwright screenshot으로 레이아웃은 확인했다. Node 20.18.1에서는 Vite가 20.19+ 또는 22.12+ 필요 경고를 내지만 build는 완료됐다.
