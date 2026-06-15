# 숙소 체크인 04 - 자료함 채팅과 인라인 근거

상태: 질문 기반 `ChatAnswer` 응답과 채팅 인라인 근거 렌더링을 연결함.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

사용자가 체감하는 첫 제품 동작은 채팅 답변이다. 이번 단계는 자료함에 질문했을 때 고정된 fact checklist가 아니라 사용자 질문 자체로 `RetrievedSource` 후보를 찾고, 그 후보가 참조하는 `SourceUnit` 원문에 근거한 `ChatAnswer`와 inline evidence를 보여주는 데까지를 닫는다.

## 사용자 장면

사용자가 전체 자료함에 묻는다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

## Goal

- 사용자 질문이 채팅에 남는다.
- 답변은 사용자가 실제로 물은 항목을 먼저 다룬다.
- 체크인 날짜처럼 PDF에 근거가 있는 질문은 `근거 있음`으로 답한다.
- 답변 안에서 PDF 본문 근거 snippet을 볼 수 있다.
- 체크인 시작 시각은 검증된 `EvidenceRef`가 없으면 값을 만들지 않고 `근거 부족`으로 보인다.
- 자료가 없거나 PDF 파싱 실패 상태이면 질문 흐름이 그 상태를 보여준다.

## Rules

- `apps/client/App.tsx`는 ready material id와 질문을 보내고, 서버가 만든 answer state를 채팅 메시지에 연결한다.
- `ChatWorkspace`는 단순 문자열 답변만이 아니라 항목별 상태와 근거를 표시할 수 있어야 한다.
- 한 답변 안에서 필요하면 `근거 있음`과 `근거 부족` 항목을 나눠 보여준다.
- `/api/questions`는 사용자 질문을 retrieval query로 사용하고, 검색된 `RetrievedSource` 후보가 담긴 `AnswerContext`를 answer composer에 넘긴다.
- answer composer가 답변 draft와 근거 snippet을 제안하면 서버는 `SourceUnit` 원문으로 snippet을 grounding해 `EvidenceRef`를 만든다.
- chat은 고정 fact target을 채우는 흐름이 아니다. 03의 `FactCandidate`는 카드/정형 후보로 이어질 수 있는 extraction 내부 재료이지, 사용자-facing `ChatAnswer`의 앞면을 지배하지 않는다.
- 검증된 `EvidenceRef`가 없는 값을 말할 때는 현재 등록된 자료에서 근거를 찾지 못했다는 식으로 원본 범위를 드러낸다.
- `/api/questions`의 기본 product 응답은 `answer`를 중심으로 둔다. 과거 retrieval smoke용 excerpt나 raw `FactCandidate`/debug reason을 사용자-facing 응답처럼 함께 노출하지 않는다.

## Non-goals

- 긴 대화 기억.
- 모든 질문 의도 분류.
- 답변 문장 스타일 고도화.
- 카드 초안 생성은 05에서 다룬다.
- Agoda HTML 메일 본문까지 자동으로 찾아 답변하기.

## 현재 코드에서 볼 곳

- `apps/server/schemas/answers.py`: `ChatAnswer`와 항목별 상태/근거 응답 계약.
- `apps/server/answers/library_chat.py`: 사용자 질문과 `AnswerContext`의 `RetrievedSource` 후보에서 grounded `ChatAnswer`를 만든다.
- `apps/server/api/routes/questions.py`: `/api/questions` route는 요청을 받아 `AskQuestionUseCase`에 넘긴다.
- `apps/server/use_cases/questions.py`: ready material selection, retrieval, `AnswerContext`, `ChatAnswer` composer, `QuestionResponse` 생성을 연결한다.
- `apps/server/retrieval/search.py`: lexical fallback에서 반복 단어가 후보 순서를 과하게 부풀리지 않도록 unique term presence로 점수화한다.
- `apps/client/App.tsx`: 질문 응답의 `answer`를 assistant message에 싣는다.
- `apps/client/components/ChatWorkspace.tsx`: 답변 항목, 상태 pill, inline evidence snippet을 렌더링한다.
- `apps/client/types.ts`: client의 `QuestionResponse`와 `ChatAnswer` 타입.

## 현재 구현 관찰

- 확인용 Agoda 예약 PDF로 실제 API를 확인했을 때, `체크인 날짜가 어떻게 돼?`는 `2025년 3월 9일`을 `근거 있음`으로 답하고 확인용 PDF `p.1 u.1` 근거 snippet을 붙인다.
- 같은 PDF에서 `체크인 시작 시각은 몇 시야?`는 날짜를 시작 시각처럼 쓰지 않고 `근거 부족`으로 남긴다.
- LLM이 PDF 추출 공백 때문에 evidence snippet을 사람이 읽는 형태로 반환하면, 서버는 `SourceUnit` 안에서 숫자 값이 순서대로 존재하는 좁은 원문 window로 `EvidenceRef`를 복구한다.
- 현재 PDF에는 체크인 날짜는 있지만 체크인 시작 시각은 없어 `근거 부족`이 맞다. companion source가 추가되면 같은 `ChatAnswer` 계약 안에서 시작 시각도 `근거 있음`으로 바뀔 수 있다.
- 기본 `/api/questions` 응답은 `answer` 중심이고, 02의 과거 smoke `excerpt`와 03의 raw `FactCandidate`/facts/debug reason은 product 응답에 함께 싣지 않는다.

## 이번 AC

1. 사용자가 질문하면 assistant 답변이 나온다.
2. 체크인 날짜 질문은 PDF의 Arrival/체크인 날짜를 `근거 있음`으로 답한다.
3. 체크인 시작 시각 질문은 날짜만 보고 시간을 만들지 않고 `근거 부족`으로 답한다.
4. PDF 근거 snippet을 답변 안에서 확인할 수 있다.
5. 답변은 등록되지 않은 companion source 값을 PDF 근거처럼 말하지 않는다.

## 남은 판단

- 근거를 항상 펼쳐 보일지, 접었다 펼치는 UI로 둘지.
- 한 질문 안에서 두 항목을 한 답변 카드로 보여줄지, 항목별 작은 블록으로 나눌지.
- raw `FactCandidate`/facts, retrieval excerpt, proposer reason 같은 debug/raw 응답을 별도 개발자용 endpoint나 mode로 다시 열지 여부.
