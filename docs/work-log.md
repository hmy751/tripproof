# 작업 로그

나중 결정에 영향을 주는 작업만 짧게 남긴다.

## 2026-05-28 - 초기 구조 정리

- 바뀐 것: README, product/eval/fixture/docs 디렉토리, spec/decision/work-log/eval run 자리를 추가했다.
- 다음: 자료를 넣고 결과를 확인할 수 있는 가장 작은 product path를 만든다.

## 2026-05-30 - preview UX 통합 / chat-first 채택 / 상태 2축

- 바뀐 것: chat-first preview(`docs/archive/preview/prd.md` + `docs/archive/preview/tripproof-preview-c.html`)를 제품 1차 경험으로 채택했다. `docs/product-model.md` 통합 모델 기준 문서를 신설하고, moment-first 입구와 "채팅=Later Feature" 프레이밍을 버렸다. 상태를 근거 축(EvidenceState)과 결정 축(ReviewDecision·카드 출처) 2축으로 분리해 "확인 필요"(needs_review)와 "직접 확인"(user 카드 출처)의 어휘 과부하를 풀었다. acceptance·AI Must Not·도메인 타입 이름·eval 축은 보존했다. 자세한 근거는 `docs/decisions/2026-05-30-preview-integration-chat-first.md`.
- 다음: 코드 드리프트 follow-up(문서만으로 닫지 않음, 구현 slice에서 판단) — `TripFact.confidence: number`의 UI 노출 여부와 필드 존치, `TripFact.value`의 `string | null` 확장, 결정 축(ReviewDecision/카드 출처)과 `category` 축의 공유 타입 승격.
