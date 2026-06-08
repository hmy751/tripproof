# 숙소 체크인 03 - Retrieval과 Evidence-backed fact

상태: sub-spec draft.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

02에서 source unit과 RAG search boundary가 준비되어도, 그것만으로 제품 답변이 되지는 않는다. 이번 단계는 질문이나 extraction target으로 retrieval candidate를 찾고, source unit 원문으로 grounding한 뒤 `TripFact`, `EvidenceRef`, `EvidenceState`를 만드는 상태 계약을 닫는다.

Retrieval candidate는 관련 있어 보이는 후보일 뿐이다. `supported` fact는 source unit 원문 일부를 `EvidenceRef`로 붙일 수 있을 때만 나온다.

## 사용자 장면

사용자는 자료함에 넣은 Agoda 예약 확정 PDF를 바탕으로 체크인 때 무엇을 보여줘야 하는지와 체크인 시작 시각을 확인하고 싶다.

## Goal

- evidence-backed fact 생성 입력은 02의 source unit, embedding record, 그리고 질문 또는 extraction target을 받는다.
- retrieval은 source unit 후보나 context pack을 만든다.
- 체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해야 한다는 fact가 나온다.
- 예약 확정서 제시 fact에는 실제 PDF 본문 일부가 `EvidenceRef`로 붙는다.
- 체크인 날짜와 체크아웃 날짜는 날짜 정보로만 다룬다.
- 체크인 시작 시각은 source unit 원문으로 grounding되지 않으면 value 없이 `근거 부족`으로 남는다.
- `근거 부족`은 fact/candidate로 직접 표현한다. 그래야 04 채팅이 값을 만들지 않고 부족 상태를 보여줄 수 있다.
- 등록되지 않은 companion source의 값을 PDF 근거처럼 만들지 않는다.
- 예약번호, 고객명, 회원 ID, 결제 카드, 숙소 연락처, 정확한 주소는 일반 `supported` fact로 자동 승격하지 않는다.
- 화면이나 답변은 fact와 상태를 받아서 보여준다.

## Rules

- 첫 구현은 Python backend의 fact 생성 함수가 맡는다.
- retrieval score, vector similarity, keyword match만으로 `supported`를 만들지 않는다.
- `supported`는 source unit 원문을 가리키는 `EvidenceRef` 없이는 나올 수 없다.
- `EvidenceRef.snippet`은 실제 source unit text의 일부여야 한다.
- `EvidenceRef.locator`는 처음에는 파일명과 page 정도로 충분하다.
- `missing` fact는 value가 없고 evidence가 비어 있을 수 있다.
- 민감하거나 애매한 값은 03에서 감지/flag 또는 `needs_review`까지만 다룬다. 자동 카드 제외와 대시보드 반영 금지는 05/06에서 닫는다.
- retrieval candidate를 그대로 `EvidenceRef`로 쓰지 않는다. candidate는 source unit 원문 확인을 거쳐야 한다.
- 외부 LLM을 붙일 때도 같은 입력과 출력 기준을 유지한다.
- 삭제한 `src/server/trip-facts/extractTripFacts.ts`의 late arrival 고정값은 이 장면 기준과 맞지 않는다. Python backend 전환 중 유지하지 않는다.

## Non-goals

- 모든 숙소 필드 추출.
- conflict 전체 처리.
- 민감정보 표시 세부 정책 완성.
- AI 답변 문장 스타일 고도화.
- Agoda HTML 메일 본문 companion source 병합.
- 카드 초안 생성이나 대시보드 반영.

## 현재 코드에서 볼 곳

- `apps/server/api/routes/questions.py`: 02 slice에서 source unit 기반 excerpt와 locator/source unit id를 반환하는 smoke 경로가 있다. 03에서는 이 결과를 accepted evidence로 바로 쓰지 않는다.
- `apps/server/materials/pdf.py`: PDF 본문 추출 경계.
- `apps/server/retrieval/`: 02 source unit과 RAG search boundary가 있다. 03에서는 retrieval 후보/context pack과 grounding 경계를 추가한다.
- `apps/server/extraction/checkin.py`: 체크인 fact 생성이 들어갈 자리.
- `apps/server/extraction/evidence.py`: `EvidenceRef` helper가 들어갈 자리.
- `apps/server/extraction/sensitive.py`: 민감정보 감지/flag가 들어갈 자리.
- `apps/server/schemas/`: backend API 응답 스키마.
- 삭제된 `src/server/trip-facts`, `src/shared`, `src/ai`의 고정값/fixture 기준은 유지하지 않는다.

## 기본 흐름

```text
SourceUnit[] / EmbeddingRecord[] / question or extraction target
-> RetrievalCandidate[] / ContextPack
-> grounding against SourceUnit.text
-> TripFact(label, value, evidenceState, evidence, sensitive?)
-> 04 ChatAnswer 입력
```

## 이번 AC

1. 예약 확정서 제시 안내는 source unit 원문으로 grounding될 때만 `근거 있음` fact로 나온다.
2. 예약 확정서 제시 근거는 Agoda PDF에서 파싱한 본문 일부를 보여준다.
3. 체크인 시작 시각은 source unit 원문으로 grounding되지 않으면 value 없이 `근거 부족` fact로 나온다.
4. 체크인 제시물 근거 source가 없으면 해당 fact가 `근거 있음`으로 나오지 않는다.
5. 예약번호, 고객명, 결제 카드 같은 민감 필드는 일반 `supported` fact로 자동 승격하지 않는다.

## 남은 판단

- 민감정보를 `needs_review` fact로 남길지, fact 생성 단계에서 제외하고 debug reason만 남길지.
- 체크인 날짜/체크아웃 날짜를 03에서 함께 fact로 만들지, 1차 구현에서는 제시물과 시작 시각만 닫을지.
- missing fact의 reason 문구를 backend schema에 둘지, 04 chat wording에서 만들지.
