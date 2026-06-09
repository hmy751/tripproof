# 2026-06-09 - 민감정보는 fixture 마스킹 경계로만 다룬다

## 맥락

숙소 체크인 카드 초안 작업 중, 공개 fixture와 공개 문서에 실제 예약 식별값을 남기지 않기 위한 주의가 제품 기능 제한으로 확장되어 있었다. 그 결과 민감정보 여부가 별도 `sensitive` 필드, `needs_review` 분기, 자동 카드 후보 제외, 자동 저장 금지 같은 제품 동작 기준처럼 문서와 코드에 남았다.

이 방향은 TripProof의 현재 제품 흐름과 맞지 않는다. 카드 초안과 대시보드의 핵심 경계는 민감정보 여부가 아니라 `자료 근거가 있는가`, `사람이 값을 확인하거나 수정했는가`, `사용자가 확정했는가`다.

## 근거

- 가장 직접적인 문제는 개발 흐름을 막는 비용이었다. 민감정보 제한을 제품 기능으로 두면 extraction, evidence state, API schema, prompt, test, 카드 초안, 대시보드 eligibility마다 별도 분기와 예외가 생기고, 카드 초안 흐름의 핵심인 `grounded answer -> card draft -> user confirmation`보다 정책 gate 구현이 앞서게 된다.
- TripProof의 상태 모델은 근거 축과 결정 축을 분리한다. 민감정보 여부는 자료가 답을 뒷받침하는지(`supported`, `needs_review`, `missing`, `conflict`)를 설명하지 못하고, 사용자가 카드를 확정했는지도 설명하지 못한다.
- `needs_review`는 근거가 있지만 표현이 애매하거나 원문 확인이 필요한 상태다. 식별값이라는 이유만으로 `needs_review`로 바꾸면, 실제로는 근거가 있는 답변을 불확실한 답변처럼 표시하게 된다.
- 카드 초안과 대시보드의 안전 경계는 모든 항목에 적용되는 사용자 확정이다. 민감정보만 별도로 막으면 근거가 있는 답변도 카드 초안으로 넘기지 못하고, 사용자가 직접 확인해 카드로 올리는 흐름과 충돌한다.
- 공개 fixture와 공개 문서의 식별값 마스킹은 자료 관리 문제다. 이 경계는 sample을 만들거나 공개 문서를 쓸 때 적용하면 되고, 제품 런타임의 답변·후보·카드 eligibility 규칙으로 들어갈 필요가 없다.

## 결정

- 민감정보 여부를 제품 기능 제한 축으로 쓰지 않는다.
- 답변 item, 카드 초안, 대시보드 카드 eligibility를 민감정보라는 이유로 막지 않는다.
- `EvidenceState`는 근거 있음, 확인 필요, 근거 부족, 자료 충돌 같은 근거/불확실성 상태만 표현한다. 민감정보 여부를 evidence state로 섞지 않는다.
- 카드 초안은 사용자가 올리고 편집할 수 있으며, 사람이 값을 수정하거나 직접 입력하면 `직접 확인` 출처로 구분한다.
- 답변, 후보, 초안이 대시보드나 현장 카드로 자동 확정되지 않는 경계는 모든 정보에 적용되는 사용자 확정 경계다. 민감정보 전용 제한이 아니다.
- 공개 fixture, 공개 sample, 공개 문서에는 실제 예약번호, 주소, 연락처, 결제정보 같은 식별값을 그대로 남기지 않는다. 이 경계는 제품 기능 제한이 아니라 공개 자료 관리 기준이다.

## 기각 또는 보류

- `FactProposal`, `FactCandidate`, API response에 `sensitive` 필드를 두는 방향은 기각한다.
- 민감정보 감지 모듈이나 denylist로 카드 초안 생성, 후보 생성, 대시보드 반영을 막는 방향은 기각한다.
- "민감정보 자동 카드 제외"를 별도 slice나 AC로 유지하지 않는다.
- archive, 기존 work-log, 기존 decision, 과거 research memo는 당시 판단과 조사 맥락을 담은 기록이므로 현재 기준에 맞추기 위해 수정하지 않는다. 현재 실행 기준으로 승격하지 않고, active product docs와 code만 새 결정에 맞춘다.

## 검증

- active client/server 코드에서 `sensitive` 기반 기능 제한을 제거했다.
- active PRD, product model, roadmap, feature specs, spec examples에서 민감정보를 제품 기능 제한으로 읽히는 문구를 제거했다.
- 공개 fixture와 공개 스펙의 placeholder/마스킹 경계는 유지했다.
- `npm run build`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest apps/server/tests -q -p no:cacheprovider`

## 이번 결정 밖

- 공개 fixture를 어떤 placeholder 값으로 만들지.
- 실제 private 자료를 화면에 표시할 때의 세부 디자인.
- 서버 저장, 동기화, 장기 보존 정책.
