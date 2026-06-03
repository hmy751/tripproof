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
- 남은 관찰: 구조 정비를 실제로 하면 `decisions/`에 결정 노트를 남기고 README·`00-spec-driven-development.md`의 구조 색인을 맞춘다(AI 위치 베이스라인 변경). 관련 MVP 판단은 현재 코드 상태와 사용자 요청에서 다시 닫는다.
