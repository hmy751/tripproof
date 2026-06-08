# 숙소 체크인 확인 - Airbnb 강릉 sanitized source

작성일: 2026-06-06

상태: feature spec. 이 문서는 `docs/specs/README.md`의 light spec-driven 기준을 따라, 실제 Airbnb 강릉 숙소 자료에서 만든 공개 가능한 source note를 바탕으로 숙소 체크인 확인 slice의 제품 동작을 잡는다.

## 원천 경계

이번 spec의 직접 원천은 `docs/material-research/2026-06-04-travel-materials-codex/sanitized-airbnb-gangneung-checkin.md`다. 공개 spec에는 Gmail message id, 원본 URL, 예약 코드, 영수증 ID, 결제 정보, 정확한 주소, 지도 좌표, 호스트 식별자, 수신자 정보를 옮기지 않는다.

`private/gmail-travel-lookup.md`는 local-only 재조회 인덱스다. 이 spec의 product 근거로 직접 인용하지 않고, 필요할 때 원본 존재를 다시 찾는 내부 경로로만 둔다.

이 문서에서 실제 값으로 다루는 것은 source note가 공개 경계로 정리한 체크인 시작 시간 `15:00`과 체크아웃 시간 `11:00`뿐이다. 그 밖의 원문 세부값은 source note의 경계를 따른다. 이번 spec의 초점은 체크인 질문에 대한 제품 답변 동작이다.

## Light Brief

```text
왜 지금: TripProof의 첫 product proof를 실제 연구 자료에 기대는 숙소 체크인 장면으로 좁힌다.
사용자 장면: 사용자가 Airbnb 강릉 예약 확정과 호스트 메시지를 자료함에 넣고 "체크인은 몇 시부터야? 늦게 도착하면 어떻게 해야 해?"라고 묻는다.
먼저 고를 slice: sanitized source text를 통해 체크인 시작 시간은 `근거 있음`, 늦은 도착 조건은 `근거 부족`으로 채팅 답변과 인라인 근거까지 잇는다.
이번 AC: 체크인 시작 시간 `근거 있음`; 늦은 도착 조건 `근거 부족`.
주의할 점: 호스트 메시지의 "판매/숙소 페이지 확인" 안내를 late arrival 조건으로 추정하지 않는다.
남은 판단: 직접 확인 카드까지 같은 구현 턴에 닫을지, 답변 slice 뒤 별도 slice로 뺄지 다시 고른다.
```

## 사용자 장면

사용자는 숙소 근처로 이동 중이거나 체크인 전날이다. Airbnb 예약 확정 이메일과 호스트 메시지가 자료함에 있고, 전체 자료함에 아래처럼 묻는다.

```text
체크인은 몇 시부터야? 늦게 도착하면 어떻게 해야 해?
```

사용자는 긴 예약 메일이나 앱 상세 화면을 다시 뒤지지 않고, 답이 어느 자료에 근거하는지와 자료가 말하지 않는 부분을 함께 알고 싶다.

## Goal

사용자는 체크인 시작 시간이 `15:00`임을 근거와 함께 확인한다. 현재 확인된 자료에 늦은 도착 조건의 구체 값이 없으면 AI는 값을 만들지 않고 `근거 부족`으로 멈춘다.

## Rules

- 자료에 있는 문장으로만 답한다.
- `근거 있음` 답변은 최소 하나의 인라인 근거를 가진다.
- 늦은 도착 조건은 현재 source note에 구체 값이 없으므로 일반 숙소 지식이나 Airbnb 도움말 지식으로 보충하지 않는다.
- 호스트 메시지의 "판매/숙소 페이지 확인" 안내는 보조 맥락일 뿐, late arrival 조건의 값이 아니다.
- 사용자가 직접 확인해 값을 채워 올리는 흐름은 허용하되, 그 카드는 `직접 확인` 출처로 구분한다.

## Non-goals

- 실제 Airbnb 원문 본문, Gmail message id, private URL, 예약번호, 정확한 주소, 결제정보를 spec에 보존하지 않는다. 이는 공개 원천 경계이며, 이번 slice의 제품 AC로 삼지는 않는다.
- 실제 Gmail ingestion, PDF/OCR, Airbnb 앱 화면 파싱 품질은 먼저 고를 slice의 통과 조건이 아니다.
- late arrival 조건, 출입 방법, 주차, wifi, house rules를 한 번에 완성하지 않는다.
- 영수증의 환불 정책을 체크인 답변으로 확장하지 않는다. 환불 조건 확인은 별도 질문이나 slice로 둔다.

## 상태 언어

| 상황 | 사용자 문구 | 이번 spec에서의 의미 |
| --- | --- | --- |
| 예약 확정 자료에서 체크인 시작 시간이 확인됨 | 근거 있음 | `15:00` 답변과 후보가 source note 기반 근거를 가진다 |
| 늦은 도착 조건의 구체 값이 현재 자료에 없음 | 근거 부족 | 값을 만들지 않고 직접 확인 여지를 남긴다 |
| 사용자가 직접 확인한 late arrival 값을 입력함 | 직접 확인 | AI 근거 카드와 구분되는 카드가 된다 |

## 구현면 펼치기

구현면은 작업 목록이 아니라, 사용자 장면이 화면까지 통과하려면 어떤 큰 면을 지나야 하는지 보는 지도다.

| 구현면 | 이번 장면에서 필요한 이유 | 현재 코드/문서 비교 | 이번에 열어둘 경계 |
| --- | --- | --- | --- |
| 자료 입력 / ingest | 예약 확정과 호스트 메시지가 자료함의 근거가 되어야 한다 | sanitized source note가 현재 안전한 원천이다. `src/ai/examples/accommodation_checkin.json`은 late arrival 값이 있어 그대로 seed로 쓰기 어렵고, source note 기준 sample 자료로 바꿔야 한다 | 실제 Gmail/PDF/OCR ingestion은 뒤로 둔다 |
| AI 후보 생성 / adapter | 체크인 시작 시간 후보와 late arrival missing 후보가 필요하다 | `src/ai/tripproof_ai/baseline.py`는 텍스트에서 체크인 시간을 뽑고, late arrival 문구가 없으면 만들지 않는다 | real LLM provider 품질은 뒤로 둔다 |
| 정규화 / 상태 언어 | 후보를 `근거 있음`, `근거 부족`으로 나눠야 한다 | `src/server/trip-facts/normalizeTripFacts.ts`는 evidence 없는 후보를 `missing`으로 둔다 | missing reason 세분화는 뒤로 둔다 |
| 채팅 답변 | 사용자가 전체 자료함에 묻고 답을 받아야 한다 | client에는 chat workspace shell과 empty draft panel이 있지만, 실제 답변 생성과 초안 생성 흐름은 아직 닫혀 있지 않다 | rich chat UX보다 상태 문구와 근거 표시를 먼저 본다 |
| 인라인 근거 | `근거 있음` 답변은 source snippet을 보여야 한다 | `EvidenceRef`는 artifact, locator, snippet을 가진다 | 이미지 영역 근거 표시는 뒤로 둔다 |
| 카드 초안 / 대시보드 | 답변이 자동 확정되지 않고 사람이 검토해야 한다 | preview와 PRD는 CardDraft, DashboardCard 경계를 둔다 | full card editing UX는 뒤로 둔다 |

주의: `src/server/trip-facts/extractTripFacts.ts`의 현재 deterministic stub은 late arrival 값을 고정으로 만든다. Airbnb 강릉 source 기준 product proof에서는 이 값을 근거로 쓰면 안 된다. 이번 slice는 sanitized source에 late arrival 구체 조건이 없을 때 `근거 부족`으로 멈추는 쪽을 기준으로 둔다.

## Slice 후보

| 후보 | 관통하는 구현면 | 실제로 닫는 제품 동작 | stub으로 둘 것 | 선택 판단 |
| --- | --- | --- | --- | --- |
| 체크인 시작 시간 답변 | 자료 입력 / 후보 생성 / 정규화 / 채팅 / 인라인 근거 | 사용자가 질문하면 `15:00`이 `근거 있음`과 근거로 보인다 | real ingestion, real LLM, dashboard persistence | 먼저 고를 slice로 적합 |
| 늦은 도착 조건 근거 부족 | 자료 입력 / 후보 생성 / 정규화 / 채팅 | 자료에 값이 없으면 late arrival 값을 만들지 않고 `근거 부족`으로 멈춘다 | 직접 확인 카드 | 체크인 답변과 같이 관찰할 수 있는 보호 slice |
| 근거 부족에서 직접 확인 카드로 | 채팅 / 카드 초안 / 대시보드 출처 | 사용자가 직접 확인한 late arrival 값을 채우면 `직접 확인`으로 오른다 | 실제 호스트 연락 workflow | 다음 slice 후보 |
| 환불 정책 확인 | 자료 입력 / 질문 라우팅 / 답변 | 영수증의 환불 문구를 별도 질문으로 확인한다 | 결제/환불 domain 전체 | 이번 숙소 체크인 slice 밖 |

## 먼저 고를 slice

먼저 고를 slice는 `체크인 시작 시간 답변 + 늦은 도착 조건 근거 부족`이다. 하나의 사용자 질문 안에서 `근거 있음`과 `근거 부족`을 같이 관찰한다.

실제로 닫는 면은 `sanitized source text -> 후보 생성 -> 상태 정규화 -> 채팅 답변 -> 인라인 근거`다. 실제 Gmail ingestion, 실 Airbnb 원문 보존, full card editing, dashboard persistence는 이번 통과 조건으로 보지 않는다.

## 이번 AC

1. 사용자가 "체크인은 몇 시부터야?"라고 물으면 답변은 `15:00`을 말하고 `근거 있음`과 인라인 근거를 함께 보여준다.
2. 사용자가 "늦게 도착하면 어떻게 해야 해?"라고 물으면 현재 자료에 구체 조건이 없으므로 값을 만들지 않고 `근거 부족`으로 멈춘다.

## 확인 방법

- sample 자료는 `sanitized-airbnb-gangneung-checkin.md`의 공개 가능한 형태만 참고한다.
- booking confirmation artifact에는 체크인 시작 시간 `15:00`과 체크아웃 `11:00`만 둔다.
- host message artifact에는 "체크인 시간과 이용 유의사항은 판매/숙소 페이지에서 확인" 수준만 두고, late arrival 구체 조건은 넣지 않는다.
- 화면 또는 product result에서 체크인 시간 답변이 `근거 있음`과 근거 snippet을 가진다.
- late arrival 답변이 `22:00 이후 연락`, `셀프 체크인 가능` 같은 값을 만들지 않는다.

## Placeholder 참고

아래 표는 sample 자료를 만들 때 원문 세부값을 옮기지 않기 위한 참고다. 이번 slice의 기능 요구나 별도 정책으로 보지 않는다.

| 원본 필드 유형 | placeholder 표현 | 참고 |
| --- | --- | --- |
| 숙소명/객실명 | `[PROPERTY_TITLE]` | 실제 숙소 식별값을 쓰지 않는다 |
| 호스트명/전화번호 | `[HOST_NAME]`, `[PHONE_NUMBER]` | 개인 또는 사업자 식별값을 쓰지 않는다 |
| 정확한 주소/지도 좌표 | `[EXACT_ADDRESS]`, `[MAP_COORDINATES]` | 실제 방문 위치를 쓰지 않는다 |
| 예약 코드/확인 코드/영수증 ID | `[RESERVATION_CODE]`, `[RECEIPT_ID]` | 예약/영수증 식별자를 쓰지 않는다 |
| private itinerary/message/receipt link | `[PRIVATE_LINK]` | 인증 또는 추적 token이 붙은 URL을 쓰지 않는다 |
| 결제 수단/금액 | `[PAYMENT_METHOD]`, `[AMOUNT]` | 결제 세부값을 쓰지 않는다 |
| 수신자 이름/이메일 | `[GUEST_NAME]`, `[GUEST_EMAIL]` | 개인 수신자 정보를 쓰지 않는다 |
| 출입/도어/락박스 코드 | `[ACCESS_CODE]` | 실제 출입 코드를 쓰지 않는다 |

## 보류 질문

- late arrival `근거 부족` 답변에서 바로 카드 초안을 열지, 다음 slice에서 직접 확인 카드까지 잇는지.
- 서버 deterministic stub을 Airbnb 강릉 source 기준으로 바꾸는 작업을 이번 slice 구현에 포함할지.
- 현재 product model 문서의 일부 타입 설명이 `TripFact.value`를 확장 후보로 말하지만 실제 공유 타입은 이미 `string | null`이다. 문서 정렬을 별도 작은 정리로 다룰지.
