# 숙소 체크인 03 - Retrieval과 Evidence-backed fact candidate

상태: Supabase vector retrieval context와 Ollama LLM fact proposer를 질문 route의 check-in candidate 생성 경로에 연결함.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

02에서 source unit과 RAG search boundary가 준비되어도, 그것만으로 제품 답변이 되지는 않는다. 이번 단계는 질문이나 extraction target으로 retrieval candidate를 찾고, LLM/extractor가 후보 원문을 읽어 체크인 fact 후보를 만들며, backend validator가 source unit 원문으로 evidence snippet과 상태를 검증해 04 `ChatAnswer` 입력을 만든다.

`TripFact`, `EvidenceRef`, `EvidenceState`는 제품 도메인 어휘로 유지한다. 다만 03의 첫 구현 산출물은 카드나 대시보드까지 확정된 완성 `TripFact`가 아니라, 04 채팅이 소비할 수 있는 evidence-backed fact candidate/item이다.

Retrieval candidate는 관련 있어 보이는 후보일 뿐이다. LLM/extractor 출력도 검증 전에는 accepted evidence가 아니다. `supported` candidate는 source unit 원문 일부를 `EvidenceRef`로 붙일 수 있을 때만 나온다.

## 사용자 장면

사용자는 자료함에 넣은 Agoda 예약 확정 PDF를 바탕으로 체크인 때 무엇을 보여줘야 하는지와 체크인 시작 시각을 확인하고 싶다.

## Goal

- evidence-backed fact candidate 생성 입력은 02의 source unit, embedding record, 그리고 질문 또는 extraction target을 받는다.
- retrieval/RAG는 LLM/extractor가 읽을 source unit 후보나 context pack을 만든다.
- LLM/extractor는 후보 원문을 읽고 label, value 또는 value 없음, evidence snippet, reason, sensitive 여부를 제안한다.
- backend validator는 제안된 evidence snippet이 실제 source unit 원문 일부인지 확인한 뒤에만 `supported`로 받아들인다.
- 체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해야 한다는 fact candidate가 나온다.
- 예약 확정서 제시 candidate에는 실제 PDF 본문 일부가 `EvidenceRef`로 붙는다.
- 체크인 날짜와 체크아웃 날짜는 날짜 정보로만 다룬다.
- 체크인 시작 시각은 source unit 원문으로 grounding되지 않으면 value 없이 `근거 부족`으로 남는다.
- `근거 부족`은 candidate/item으로 직접 표현한다. 그래야 04 채팅이 값을 만들지 않고 부족 상태를 보여줄 수 있다.
- 등록되지 않은 companion source의 값을 PDF 근거처럼 만들지 않는다.
- 예약번호, 고객명, 회원 ID, 결제 카드, 숙소 연락처, 정확한 주소는 일반 `supported` candidate로 자동 승격하지 않는다.
- 04 채팅은 이 candidate/state/evidence를 입력으로 받아 답변 화면에 표시한다.

## Rules

- 첫 구현은 Python backend의 grounded extractor/adapter와 validator가 맡는다. RAG는 읽을 후보를 고르고, LLM/extractor는 후보 원문을 해석하며, validator는 source unit 원문으로 evidence와 상태를 확인한다.
- 실제 LLM provider 품질이나 프롬프트 고도화는 뒤로 둘 수 있다. 그래도 hard-coded answer나 fixture value가 RAG/LLM/evidence 인과를 대신하면 안 된다.
- retrieval score, vector similarity, keyword match만으로 `supported`를 만들지 않는다.
- LLM/extractor 출력만으로도 `supported`를 만들지 않는다. `supported`는 validator를 통과해야 한다.
- `supported`는 source unit 원문을 가리키는 `EvidenceRef` 없이는 나올 수 없다.
- `EvidenceRef.snippet`은 실제 source unit text의 일부여야 한다.
- `EvidenceRef.locator`는 처음에는 파일명과 page 정도로 충분하다.
- `missing` fact는 value가 없고 evidence가 비어 있을 수 있다.
- 민감하거나 애매한 값은 03에서 감지/flag 또는 `needs_review`까지만 다룬다. 자동 카드 제외와 대시보드 반영 금지는 05/06에서 닫는다.
- retrieval candidate를 그대로 `EvidenceRef`로 쓰지 않는다. candidate는 source unit 원문 확인을 거쳐야 한다.
- 외부 LLM을 붙일 때도 같은 입력과 출력 기준을 유지한다. provider를 바꿔도 `자료 -> retrieval 후보 -> LLM/extractor 판단 -> 원문 검증 -> 상태` 인과는 유지한다.
- 삭제한 `src/server/trip-facts/extractTripFacts.ts`의 late arrival 고정값은 이 장면 기준과 맞지 않는다. Python backend 전환 중 유지하지 않는다.

## Non-goals

- 모든 숙소 필드 추출.
- conflict 전체 처리.
- 민감정보 표시 세부 정책 완성.
- LLM provider 선택, 운영 프롬프트 품질, 모델 평가 고도화.
- AI 답변 문장 스타일 고도화.
- Agoda HTML 메일 본문 companion source 병합.
- 카드 초안 생성이나 대시보드 반영.

## 관련 코드 위치

- `apps/server/api/routes/questions.py`: source unit 기반 excerpt와 locator/source unit id를 반환하고, check-in fact candidate 생성을 호출한다. excerpt 경로의 결과를 accepted evidence로 바로 쓰지 않는다.
- `apps/server/materials/pdf.py`: PDF 본문 추출 경계.
- `apps/server/retrieval/`: source unit, embedding record, retrieval repository, Supabase vector match, lexical fallback으로 `ContextPack` 후보를 만든다.
- `apps/server/extraction/checkin.py`: check-in fact candidate 생성 경로가 있다. retrieval repository를 통해 context 후보를 받고, Ollama JSON proposer가 fact proposal을 만든 뒤 validator가 grounding한다. 테스트에서는 deterministic proposer를 주입한다.
- `apps/server/extraction/evidence.py`: proposer가 낸 snippet이 source unit 원문에 실제로 포함되는지 validator가 확인한다.
- `apps/server/extraction/sensitive.py`: 민감정보 감지/flag가 들어갈 자리.
- `apps/server/schemas/`: backend API 응답 스키마.
- 삭제된 `src/server/trip-facts`, `src/shared`, `src/ai`의 고정값/fixture 기준은 유지하지 않는다.

## 기본 흐름

```text
SourceUnit[] / EmbeddingRecord[] / question or extraction target
-> RetrievalCandidate[] / ContextPack
-> LLM/extractor proposes fact candidates from candidate source text
-> validator grounds evidence snippets against SourceUnit.text
-> Evidence-backed fact item / TripFact-shaped candidate(label, value, evidenceState, evidence, sensitive?, reason)
-> 04 ChatAnswer 입력
```

## 이번 slice의 실행 관찰

- 02의 source unit과 embedding record를 입력으로 받아 target별 `ContextPack`을 만든다.
- `TRIPPROOF_RETRIEVAL_BACKEND=supabase`에서는 ready vector가 있으면 Supabase `match_tripproof_source_units` RPC 후보를 우선 사용하고, ready vector나 match 결과가 없으면 lexical fallback 후보를 사용한다.
- `TRIPPROOF_FACT_PROPOSER_BACKEND=ollama`에서는 Ollama chat JSON proposer가 retrieval 후보 source unit만 읽어 fact proposal을 만든다.
- validator는 fact proposal의 evidence snippet이 source unit 원문에 포함될 때만 `supported` evidence로 받아들인다.
- LLM이 줄바꿈이나 공백을 정리한 snippet을 반환하면 validator가 source unit 원문 span으로 다시 grounding한다.
- 예약 확정서 제시 항목은 LLM이 맞는 source unit을 고르되 snippet을 의역한 경우 해당 source unit 원문을 evidence로 사용한다.
- 체크인 시작 시각은 LLM이 `supported`를 제안해도 실제 시간 형태가 아니면 `missing`으로 낮춘다. 날짜를 시작 시각으로 승격하지 않는다.
- 해당 slice의 실행 관찰에서는 retrieval 후보가 fact proposer와 validator를 거쳐 예약 확정서 제시 항목은 `supported`, 체크인 시작 시각은 `missing`으로 남는 흐름을 확인했다.

## 이번 AC

1. 예약 확정서 제시 안내는 source unit 원문으로 grounding될 때만 `근거 있음` candidate로 나온다.
2. 예약 확정서 제시 근거는 Agoda PDF에서 파싱한 본문 일부를 보여준다.
3. 체크인 시작 시각은 source unit 원문으로 grounding되지 않으면 value 없이 `근거 부족` candidate로 나온다.
4. 체크인 제시물 근거 source가 없으면 해당 candidate가 `근거 있음`으로 나오지 않는다.
5. 예약번호, 고객명, 결제 카드 같은 민감 필드는 일반 `supported` candidate로 자동 승격하지 않는다.

## 남은 판단

- 민감정보를 `needs_review` candidate로 남길지, fact candidate 생성 단계에서 제외하고 debug reason만 남길지.
- 체크인 날짜/체크아웃 날짜를 03에서 함께 candidate로 만들지, 1차 구현에서는 제시물과 시작 시각만 닫을지.
- missing candidate의 reason 문구를 backend schema에 둘지, 04 chat wording에서 만들지.
- Ollama proposer 실패 시 missing 처리만 둘지, retry/backoff와 사용자-facing 오류 상태를 별도로 둘지.
- LLM이 맞는 source unit을 골랐지만 snippet을 의역하는 경우 source unit 전체를 evidence로 쓰는 fallback을 다른 fact target에도 허용할지.
