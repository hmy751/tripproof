# 숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF

작성일: 2026-06-06

상태: feature spec. 이 문서는 Agoda 후쿠오카 예약 확정 PDF를 제품에 넣고, `SourceUnit` 원문으로 확인 가능한 체크인 준비 정보를 `ChatAnswer`로 답하고, 검증된 `EvidenceRef` 근거가 없는 값은 만들지 않는 흐름을 잡는다.

## 자료 경계

이번 스펙은 사용자가 보유한 Agoda 예약 확정 PDF를 기준으로 한다. 공개 스펙에는 Gmail message id, attachment id, 실제 예약 번호, 예약 토큰 URL, 회원 ID, 고객명, 결제 정보, 정확한 숙소 주소, 숙소 연락처를 옮기지 않는다.

제품 입력으로 먼저 다룰 파일은 Agoda 예약 확정 PDF 하나다. 공개 fixture를 만들 때는 실제 PDF를 그대로 commit하지 않고, 원본 구조를 본뜬 sanitized PDF나 local-only private fixture를 쓴다.

Agoda 예약 확정 PDF에서 product proof로 다룰 수 있는 내용은 다음이다.

- 예약 확정서 PDF 자체가 체크인 시 제시할 자료라는 점.
- 체크인 날짜와 체크아웃 날짜.
- 취소/노쇼 정책.
- 도시세가 체크인 시 숙소에 직접 지불될 수 있다는 안내.
- 체크인 시 신분증과 결제 카드 제시가 필요할 수 있다는 안내.

이번 스펙은 체크인 시작 시각, 체크아웃 시각, 체크인 가능 마감 같은 시간 값의 존재 여부를 문서가 미리 판정하지 않는다. 등록된 `SourceUnit` 원문으로 grounding되는 경우에만 `근거 있음`으로 다루고, 등록되지 않은 companion source의 값을 현재 PDF 근거처럼 섞지 않는다.

## 짧은 기준

```text
왜 지금: 사용자가 예약 확정 PDF를 넣고 제품이 본문을 얻는 흐름을 먼저 닫는다.
사용자 장면: 사용자가 Agoda 후쿠오카 예약 확정 PDF를 넣고 "체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?"라고 묻는다.
먼저 고를 slice: PDF 선택/추가 -> PDF 텍스트 파싱 -> SourceUnit/RAG search -> RetrievedSource/AnswerContext 구성 -> LibraryChatAnswerComposer 판단 -> SourceUnit 원문 grounding -> ChatAnswer/EvidenceRef -> 인라인 근거.
이번 AC: 예약 확정서 제시는 `SourceUnit` 원문에 근거하면 `근거 있음`, 체크인 시작 시각은 검증된 `EvidenceRef` 근거가 없으면 `근거 부족`.
주의할 점: HTML 메일 본문이나 일반 호텔 지식의 시각 값을 PDF 근거처럼 섞지 않는다.
남은 판단: Agoda HTML 메일 본문을 두 번째 companion source로 추가할지, 현재 `SourceUnit`/`EvidenceRef` proof 뒤에 별도 slice로 열지.
```

## 사용자 장면

사용자는 숙소 체크인을 앞두고 Agoda 예약 확정 PDF를 제품에 넣는다. 사용자는 PDF를 직접 열어 긴 약관과 안내를 훑지 않고, 체크인 현장에서 무엇을 보여줘야 하는지와 현재 자료에서 확인 가능한 시각 정보가 무엇인지 함께 알고 싶다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

## Goal

사용자는 `SourceUnit` 원문에 근거해 체크인 시 예약 확정서의 전자 사본 또는 인쇄본을 제시해야 한다는 답을 얻는다. 체크인 시작 시각처럼 검증된 `EvidenceRef` 근거가 없는 값은 AI가 만들지 않고 `근거 부족`으로 멈춘다.

## Rules

- 사용자가 넣은 PDF에서 파싱한 본문으로 답한다.
- PDF 파싱은 1번 하위 스펙의 포함 범위다.
- 파일 본문 없이 답변하지 않는다.
- `근거 있음` 답변은 최소 하나의 인라인 근거를 가진다.
- 검증된 `EvidenceRef` 근거가 없는 체크인 시작 시각, 체크아웃 시각, 체크인 가능 마감은 등록되지 않은 companion source나 일반 숙소 지식으로 보충하지 않는다.
- 사용자가 다른 원본에서 직접 확인한 값을 채워 올리는 흐름은 허용하되, 그 카드는 `직접 확인` 출처로 구분한다.

## Non-goals

- Gmail 계정에서 자동으로 가져오기, attachment id 저장, 원본 PDF 장기 저장은 이번 흐름에서 요구하지 않는다.
- 모든 PDF 형식을 한 번에 지원하지 않는다. 먼저 텍스트 추출 가능한 Agoda 예약 확정 PDF 한 종류를 안정적으로 읽는다.
- 스캔 이미지 PDF OCR, 표 레이아웃 완전 복원, QR/바코드 인식은 이번 범위가 아니다.
- Agoda HTML 메일 본문과 숙소 답변 메일은 companion source 후보지만 현재 `SourceUnit` boundary에는 포함하지 않는다.
- 실제 예약 PDF, 예약번호, 고객명, 결제정보, 정확한 주소를 공개 fixture나 공개 스펙에 보존하지 않는다.

## 상태 언어

| 상황 | 사용자 문구 | 이번 스펙에서의 의미 |
| --- | --- | --- |
| PDF에서 예약 확정서 제시 안내가 확인됨 | 근거 있음 | 체크인 시 보여줄 자료 답변과 후보가 PDF 본문 근거를 가진다 |
| PDF에서 체크인 날짜가 확인됨 | 근거 있음 | 날짜는 말할 수 있지만 시작 시각과 혼동하지 않는다 |
| 체크인 시작 시각을 뒷받침할 `EvidenceRef`가 없음 | 근거 부족 | 값을 만들지 않고 다른 원본 확인 여지를 남긴다 |
| 사용자가 다른 원본에서 시각을 직접 입력함 | 직접 확인 | AI 근거 카드와 구분되는 카드가 된다 |

## 하위 스펙

아래 문서는 이 기능을 한 번에 뭉뚱그리지 않기 위한 구현 단위다. 각 문서는 제품 흐름을 닫기 위한 기준이고, 구현 순서를 묶는 문서가 아니다.

| 순서 | 문서 | 닫으려는 제품 동작 |
| --- | --- | --- |
| 1 | [Agoda PDF 파일 파싱](01-file-parsing.md) | 사용자가 Agoda 예약 확정 PDF를 넣고, 제품이 본문을 파싱해 자료함과 다음 `SourceUnit`/evidence 입력으로 넘긴다 |
| 2 | [SourceUnit과 RAG search boundary](02-source-units-retrieval.md) | 파싱된 PDF 본문을 page/section `SourceUnit`으로 나누고, `search_text`/embedding이 원문 locator로 되돌아가게 한다 |
| 3 | [Retrieval과 evidence grounding boundary](03-evidence-backed-facts.md) | RAG가 고른 `RetrievedSource` 후보와 `AnswerContext`를 answer composer가 읽고, backend가 `SourceUnit` 원문으로 `EvidenceRef`를 grounding해 예약 확정서 제시는 `근거 있음`, 근거가 없는 체크인 시작 시각은 `근거 부족` `ChatAnswer` 항목으로 넘긴다 |
| 4 | [자료함 채팅과 인라인 근거](04-library-chat-evidence.md) | 사용자가 물으면 `ChatAnswer`에 PDF 근거가 붙은 답변과 검증된 `EvidenceRef`가 없는 값의 부족 상태가 채팅 화면에 보인다 |
| 5 | [카드 초안과 직접 확인](05-card-draft-confirm.md) | 근거 있는 답변을 카드 초안으로 올리고, 근거 부족 시각 값은 사용자가 직접 채운다 |
| 6 | [대시보드와 현장 카드](06-dashboard-field-cards.md) | 확정한 카드만 대시보드에, 현장 저장한 카드만 현장 탭에 보인다 |

## 구현 상태

01-06 하위 스펙은 현재 client/server product path 기준으로 한 번 이어졌다. 사용자는 PDF를 추가하고, 자료함에 질문해 근거 상태와 inline evidence가 붙은 답변을 보고, 답변 항목을 카드 초안으로 올린 뒤, 직접 확인 값을 채워 대시보드 카드로 확정할 수 있다. 현장 탭은 대시보드 카드에서 `현장 저장`을 누른 카드만 보여준다.

현재 범위는 in-memory/client state MVP다. 서버 저장/동기화, 여러 카테고리 편집, companion source 자동 추가, 오프라인 현장 패키지는 아직 구현하지 않았다.

## 구현면 펼치기

| 구현 요소 | 이번 장면에서 필요한 이유 | 현재 코드/문서 비교 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| PDF 넣기 / 파싱 | 예약 확정 PDF가 제품의 시작점이어야 한다 | 01에서 client 업로드와 `apps/server/` PDF ingest를 연결했다 | PDF 선택/추가, 텍스트 추출, 자료함 표시, 질문 입력 연결을 닫는다 |
| SourceUnit / RAG search | PDF 본문 전체가 아니라 어떤 원문 단위가 검색과 근거의 원천인지 추적해야 한다 | 02에서 first backend source/search boundary를 닫았다. ready material 생성 시 `SourceUnit`과 pending `EmbeddingRecord`가 만들어진다. 과거 02 smoke 응답면의 excerpt 계열 필드는 현재 `/api/questions` product response가 아니다 | page/section `SourceUnit`을 만들고, `search_text`/embedding record가 `SourceUnit` locator로 되돌아가게 한다 |
| Retrieval / evidence grounding | 검색 후보를 `ChatAnswer`가 소비할 `AnswerContext`와 검증 가능한 근거 상태로 바꿔야 한다 | 삭제한 `src/server/trip-facts/extractTripFacts.ts`는 late arrival 값을 고정으로 만들었다 | Python backend가 `RetrievedSource` 후보를 `LibraryChatAnswerComposer` 판단에 넘기고, `SourceUnit` 원문으로 `EvidenceRef`를 grounding해 04가 소비할 `ChatAnswer` 항목을 만든다. 검증된 근거가 없는 체크인 시작 시각은 만들지 않는다 |
| 정규화 / 상태 언어 | 후보를 `근거 있음`, `근거 부족`, `확인 필요`로 나눠야 한다 | 삭제한 `src/server/trip-facts/normalizeTripFacts.ts`의 규칙은 03 이후 Python backend schema로 다시 잡는다 | 화면에 보일 상태 언어를 backend response 상태와 맞춘다 |
| 채팅 답변 | 사용자가 전체 자료함에 묻고 답을 받아야 한다 | 04에서 질문 기반 `ChatAnswer` 응답과 인라인 근거 렌더링을 연결했다 | 질문, 답변, 상태, 근거 snippet을 한 화면에서 보이게 한다 |
| 인라인 근거 | `근거 있음` 답변은 PDF 본문 일부를 보여야 한다 | `EvidenceRef`는 `materialId`, `sourceUnitId`, `label`, `locator`, `snippet`을 가진다 | 처음은 자료명, page, snippet으로 충분하다 |
| 카드 초안 / 대시보드 | 답변이 자동 확정되지 않고 사람이 검토해야 한다 | 05에서 채팅 답변 항목을 카드 초안으로 올리고, 직접 확인 출처를 client draft state로 구분했다. 06에서 초안 확정, 대시보드 표시, 현장 저장을 client state로 연결했다 | 초안, 직접 확인, 확정, 현장 저장 흐름을 순서대로 잇는다 |

주의: 삭제한 `src/server/trip-facts/extractTripFacts.ts`의 고정값 코드는 late arrival 값을 만들었다. 현재 제품 흐름에서는 검증된 `EvidenceRef`가 없는 값을 근거로 쓰면 안 되며, Python backend 전환 중 유지하지 않는다.

## Slice 후보

| slice 후보 | 관통하는 구현면 | 실제로 닫는 product behavior | 범위를 넓힐 때 볼 것 |
| --- | --- | --- | --- |
| Agoda PDF에서 체크인 제시물 답변까지 | PDF 넣기 / 파싱 / SourceUnit / RAG search / RetrievedSource·AnswerContext / LibraryChatAnswerComposer 판단 / EvidenceRef grounding / 채팅 / 인라인 근거 | 사용자가 PDF를 넣고 질문하면 예약 확정서 제시 안내가 `SourceUnit` 원문에 근거해 `근거 있음`, PDF snippet으로 보인다 | 계정 연결, 장기 저장, 더 많은 PDF |
| 체크인 시작 시각 source 부재 처리 | PDF 넣기 / 파싱 / SourceUnit / RAG search / RetrievedSource·AnswerContext / LibraryChatAnswerComposer 판단 / EvidenceRef grounding / 채팅 | 체크인 시작 시각을 뒷받침할 `EvidenceRef`가 없으면 값을 만들지 않고 `근거 부족`으로 멈춘다 | Agoda HTML 메일 본문 companion source |
| 근거 부족에서 직접 확인 카드로 | 채팅 / 카드 초안 / 대시보드 출처 | 사용자가 다른 원본에서 확인한 체크인 시작 시각을 채우면 `직접 확인`으로 오른다 | companion source를 근거로 승격 |
| 취소/노쇼 정책 확인 | PDF 파싱 / 질문 라우팅 / 답변 | PDF의 취소/노쇼 안내를 별도 질문으로 확인한다 | 결제/환불 영역 전체 |

## 먼저 고를 slice

먼저 고를 slice는 `Agoda PDF에서 체크인 제시물 답변까지 + 체크인 시작 시각 source 부재 처리`다. 하나의 사용자 질문 안에서 `근거 있음`과 `근거 부족`을 같이 확인한다.

이번 slice에서 닫는 구현면은 `PDF 선택/추가 -> PDF 텍스트 파싱 -> SourceUnit/RAG search -> RetrievedSource/AnswerContext 구성 -> LibraryChatAnswerComposer 판단 -> SourceUnit 원문 grounding -> ChatAnswer/EvidenceRef -> 인라인 근거`다. PDF 본문 없이 만든 답변이나, `SourceUnit` 원문으로 되돌아갈 수 없는 `근거 있음`은 이 흐름을 대신할 수 없다.

## 이번 AC

1. 사용자가 Agoda 예약 확정 PDF 하나를 넣을 수 있다.
2. 제품은 PDF 본문을 읽고 자료함에 파싱 완료 상태로 보여준다.
3. 제품은 PDF 본문에서 `SourceUnit`과 검색용 `search_text`/embedding record를 만들고, 검색 결과가 `SourceUnit` locator로 되돌아가게 한다.
4. 사용자가 "체크인 때 뭘 보여줘야 해?"라고 물으면 답변은 예약 확정서 전자 사본 또는 인쇄본 제시를 말하고 `근거 있음`과 인라인 근거를 함께 보여준다.
5. 사용자가 "체크인 시간은 몇 시야?"라고 물었을 때 검증된 `EvidenceRef` 근거가 없으면 값을 만들지 않고 `근거 부족`으로 멈춘다.

## 확인 방법

1. sanitized Agoda 예약 확정 PDF 또는 local-only private PDF를 업로드한다.
2. 자료함에서 PDF 파싱 완료와 본문 일부를 확인한다.
3. `SourceUnit`과 embedding record가 PDF page/locator/snippet으로 되돌아갈 수 있는지 확인한다. 현재 product 응답에서는 `/api/questions`의 `answer.items[].evidence[]`가 이 회수 경계를 보여주며, 과거 02 smoke 응답면의 `excerptLocator`/`excerptSourceUnitId`는 public response 계약이 아니다.
4. 채팅에서 "체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?"를 묻는다.
5. 답변에 예약 확정서 제시 안내의 inline evidence가 붙고, 검증된 `EvidenceRef`가 없는 항목은 `근거 부족`으로 남는지 본다.

## Placeholder 참고

아래 표는 Agoda PDF 기준 공개 fixture를 만들 때 원문 세부값을 옮기지 않기 위한 참고다. 기능 요구가 아니라 공개 자료를 만들 때 참고하는 기준이다.

| 원본 필드 유형 | placeholder 표현 | 참고 |
| --- | --- | --- |
| 숙소명 | `[PROPERTY_TITLE]` | 실제 숙소 식별값을 쓰지 않는다 |
| 정확한 주소/숙소 연락처 | `[EXACT_ADDRESS]`, `[PHONE_NUMBER]`, `[PROPERTY_EMAIL]` | 실제 방문 위치와 연락처를 쓰지 않는다 |
| 예약 번호/예약 참조/회원 ID | `[BOOKING_ID]`, `[BOOKING_REFERENCE]`, `[MEMBER_ID]` | 예약 접근 또는 고객지원 식별자를 쓰지 않는다 |
| 고객명/거주 국가 | `[GUEST_NAME]`, `[COUNTRY]` | 개인 정보를 쓰지 않는다 |
| 결제 카드/금액 | `[PAYMENT_METHOD]`, `[AMOUNT]` | 결제 세부값을 쓰지 않는다 |
| private booking management URL | `[PRIVATE_LINK]` | 인증 또는 추적 token이 붙은 URL을 쓰지 않는다 |

## 남은 질문

- Agoda HTML 확인 메일 본문을 두 번째 원본으로 추가해 시간 정보를 별도 source 근거로 다룰지.
- 대시보드 카드의 서버 저장/동기화 계약을 언제 열지.
- 여러 일정과 카테고리를 사용자가 편집하는 UX를 어느 시점부터 제품 계약으로 고정할지.
