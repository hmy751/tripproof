# 숙소 체크인 03 - Retrieval과 evidence grounding boundary

상태: Supabase vector retrieval context와 Library Chat answer composer의 evidence grounding 경계를 현재 질문 응답 경로에 맞춰 정리함.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

02에서 `SourceUnit`과 RAG search boundary가 준비되어도, 그것만으로 제품 답변이 되지는 않는다. 현재 `/api/questions` 경로는 질문으로 `RetrievedSource` 후보와 `AnswerContext`를 만들고, Library Chat answer composer가 후보 `SourceUnit.text`를 읽어 `ChatAnswer` item을 제안하며, backend가 `SourceUnit` 원문으로 evidence snippet을 grounding해 `EvidenceRef`를 만든다.

`EvidenceRef`와 `EvidenceState`는 답변 근거 계약의 어휘로 유지한다. `FactCandidate`는 extraction 내부 후보 lane으로 남기며, 현재 Library Chat의 사용자-facing 응답 경로는 `QuestionResponse.answer` 안의 `ChatAnswer`다.

`RetrievedSource`는 관련 있어 보이는 검색 후보일 뿐이다. LLM/composer 출력도 검증 전에는 `EvidenceRef`가 아니다. `supported` `ChatAnswer` item은 `SourceUnit` 원문 일부를 `EvidenceRef`로 붙일 수 있을 때만 나온다.

## 사용자 장면

사용자는 자료함에 넣은 Agoda 예약 확정 PDF를 바탕으로 체크인 때 무엇을 보여줘야 하는지와 체크인 시작 시각을 확인하고 싶다.

## Goal

- evidence-grounded answer 생성 입력은 02의 `SourceUnit`, `EmbeddingRecord`, 그리고 사용자 질문을 받는다.
- retrieval/RAG는 answer composer가 읽을 `RetrievedSource` 후보와 `AnswerContext`를 만든다.
- Library Chat answer composer는 후보 `SourceUnit.text`를 읽고 label, value 또는 value 없음, evidence snippet을 제안한다.
- backend grounding은 제안된 evidence snippet이 실제 `SourceUnit` 원문 일부인지 확인한 뒤에만 `supported`로 받아들인다.
- 체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해야 한다는 `ChatAnswer` item이 나온다.
- 예약 확정서 제시 item에는 실제 PDF 본문 일부가 `EvidenceRef`로 붙는다.
- 체크인 날짜와 체크아웃 날짜는 날짜 정보로만 다룬다.
- 체크인 시작 시각은 `SourceUnit` 원문으로 grounding되지 않으면 value 없이 `근거 부족`으로 남는다.
- `근거 부족`은 `ChatAnswer` item의 `EvidenceState`로 직접 표현한다. 그래야 04 채팅이 값을 만들지 않고 부족 상태를 보여줄 수 있다.
- 등록되지 않은 companion source의 값을 PDF 근거처럼 만들지 않는다.
- 04 채팅은 이 `ChatAnswer` item, `EvidenceState`, `EvidenceRef`를 답변 화면에 표시한다.

## Rules

- 현재 질문 응답은 Python backend의 `AskQuestionUseCase`, retrieval, Library Chat answer composer, evidence grounding이 맡는다. RAG는 `RetrievedSource` 후보를 고르고, answer composer는 후보 원문을 해석하며, backend는 `SourceUnit` 원문으로 `EvidenceRef`와 상태를 확인한다.
- 실제 LLM provider 품질이나 프롬프트 고도화는 뒤로 둘 수 있다. 그래도 hard-coded answer나 fixture value가 RAG/LLM/evidence 인과를 대신하면 안 된다.
- retrieval score, vector similarity, keyword match만으로 `supported`를 만들지 않는다.
- LLM/composer 출력만으로도 `supported`를 만들지 않는다. `supported`는 grounding을 통과해야 한다.
- `supported`는 `SourceUnit` 원문을 가리키는 `EvidenceRef` 없이는 나올 수 없다.
- `EvidenceRef.snippet`은 실제 `SourceUnit.text`의 일부여야 한다.
- `EvidenceRef.locator`는 처음에는 파일명과 page 정도로 충분하다.
- `missing` answer item은 value가 없고 evidence가 비어 있을 수 있다.
- 애매한 값은 `needs_review`로 둘 수 있다.
- `RetrievedSource`를 그대로 `EvidenceRef`로 쓰지 않는다. 검색 후보는 `SourceUnit` 원문 확인을 거쳐야 한다.
- 외부 LLM을 붙일 때도 같은 입력과 출력 기준을 유지한다. provider를 바꿔도 `자료 -> RetrievedSource 후보 -> LLM/composer 판단 -> SourceUnit 원문 grounding -> ChatAnswer 상태` 인과는 유지한다.
- 삭제한 `src/server/trip-facts/extractTripFacts.ts`의 late arrival 고정값은 이 장면 기준과 맞지 않는다. Python backend 전환 중 유지하지 않는다.

## Non-goals

- 모든 숙소 필드 추출.
- conflict 전체 처리.
- LLM provider 선택, 운영 프롬프트 품질, 모델 평가 고도화.
- AI 답변 문장 스타일 고도화.
- Agoda HTML 메일 본문 companion source 병합.
- 카드 초안 생성이나 대시보드 반영.

## 관련 코드 위치

- `apps/server/api/routes/questions.py`: route는 `/api/questions` 요청을 얇게 받아 `AskQuestionUseCase`에 넘긴다. 현재 public response는 `QuestionResponse.answer` 중심이다.
- `apps/server/use_cases/questions.py`: ready material selection, retrieval records load, `AnswerContext` 구성, Library Chat answer composer 호출, `QuestionResponse` 생성을 잇는다.
- `apps/server/materials/pdf.py`: PDF 본문 추출 경계.
- `apps/server/retrieval/`: `SourceUnit`, `EmbeddingRecord`, retrieval repository, Supabase vector match, lexical fallback으로 `RetrievedSource` 후보와 `AnswerContext`를 만든다.
- `apps/server/answers/library_chat.py`: 사용자 질문과 `AnswerContext`에서 grounded `ChatAnswer`를 만들고, composer payload의 evidence snippet을 `SourceUnit` 원문으로 projection한다.
- `apps/server/extraction/evidence.py`: evidence snippet이 `SourceUnit` 원문에 실제로 포함되는지 확인해 `EvidenceRef`를 만든다.
- `apps/server/schemas/`: backend API 응답 스키마.
- 삭제된 `src/server/trip-facts`, `src/shared`, `src/ai`의 고정값/fixture 기준은 유지하지 않는다.

## 기본 흐름

```text
SourceUnit[] / EmbeddingRecord[] / question
-> RetrievedSource[] / AnswerContext
-> LibraryChatAnswerComposer proposes answer items from RetrievedSource source-unit text
-> server grounds evidence snippets against SourceUnit.text
-> ChatAnswerItem(label, value, evidenceState, EvidenceRef[])
-> 04 ChatAnswer response
```

## 이번 slice의 실행 관찰

- 02의 `SourceUnit`과 `EmbeddingRecord`를 입력으로 받아 Library Chat 질문용 `AnswerContext`를 만든다.
- product retrieval은 Supabase 단일 백엔드다. ready vector가 있으면 Supabase `match_tripproof_source_units` RPC 후보를 우선 사용하고, ready vector나 match 결과가 없으면 lexical fallback 후보를 사용한다.
- Library Chat answer composer는 Ollama chat JSON backend(`TRIPPROOF_OLLAMA_ANSWER_MODEL`)로 `ChatAnswer` item payload를 만든다.
- server grounding은 answer item payload의 evidence snippet이 `SourceUnit` 원문에 포함될 때만 `supported` evidence로 받아들인다.
- LLM이 줄바꿈이나 공백을 정리한 snippet을 반환하면 server grounding이 `SourceUnit` 원문 span으로 다시 grounding한다.
- 예약 확정서 제시 항목은 LLM이 맞는 `SourceUnit`을 고르되 snippet을 의역한 경우 해당 `SourceUnit` 원문에서 복구한 snippet/window를 `EvidenceRef`로 사용한다.
- 체크인 시작 시각은 LLM이 `supported`를 제안해도 실제 시간 형태가 아니면 `missing`으로 낮춘다. 날짜를 시작 시각으로 승격하지 않는다.
- 해당 slice의 실행 관찰에서는 retrieval 후보가 Library Chat answer composer와 grounding을 거쳐 예약 확정서 제시 항목은 `supported`, 체크인 시작 시각은 `missing`으로 남는 흐름을 확인했다.

## 이번 AC

1. 예약 확정서 제시 안내는 `SourceUnit` 원문으로 grounding될 때만 `근거 있음` `ChatAnswer` item으로 나온다.
2. 예약 확정서 제시 근거는 Agoda PDF에서 파싱한 본문 일부를 보여준다.
3. 체크인 시작 시각은 `SourceUnit` 원문으로 grounding되지 않으면 value 없이 `근거 부족` `ChatAnswer` item으로 나온다.
4. 체크인 제시물 근거 `EvidenceRef`가 없으면 해당 answer item이 `근거 있음`으로 나오지 않는다.

## 남은 판단

- 체크인 날짜/체크아웃 날짜를 03에서 함께 answer item으로 만들지, 1차 구현에서는 제시물과 시작 시각만 닫을지.
- missing item의 reason 문구를 backend schema에 둘지, 04 chat wording에서 만들지.
- Ollama proposer 실패 시 missing 처리만 둘지, retry/backoff와 사용자-facing 오류 상태를 별도로 둘지.
- LLM이 맞는 `SourceUnit`을 골랐지만 snippet을 의역하는 경우 `SourceUnit` 원문에서 복구한 snippet/window를 `EvidenceRef`로 쓰는 fallback을 다른 answer target에도 허용할지.
