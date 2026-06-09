# 숙소 체크인 04 - 자료함 채팅과 인라인 근거

상태: `ChatAnswer` 응답 계약과 채팅 인라인 근거 렌더링을 연결함.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

사용자가 체감하는 첫 제품 동작은 채팅 답변이다. 이번 단계는 자료함에 질문했을 때 03의 fact, 상태, 근거가 답변으로 보이는 데까지를 닫는다.

## 사용자 장면

사용자가 전체 자료함에 묻는다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

## Goal

- 사용자 질문이 채팅에 남는다.
- 답변은 체크인 제시물과 체크인 시작 시각을 함께 다룬다.
- 체크인 시 예약 확정서 전자 사본 또는 인쇄본을 제시해야 한다는 내용은 `근거 있음`으로 보인다.
- 답변 안에서 PDF 본문 근거 snippet을 볼 수 있다.
- 체크인 시작 시각은 accepted evidence가 없으면 값을 만들지 않고 `근거 부족`으로 보인다.
- 자료가 없거나 PDF 파싱 실패 상태이면 질문 흐름이 그 상태를 보여준다.

## Rules

- `apps/client/App.tsx`는 ready material id와 질문을 보내고, 서버가 만든 answer state를 채팅 메시지에 연결한다.
- `ChatWorkspace`는 단순 문자열 답변만이 아니라 항목별 상태와 근거를 표시할 수 있어야 한다.
- 한 답변 안에서 `근거 있음`과 `근거 부족` 항목을 나눠 보여준다.
- 답변의 근거 snippet은 03에서 받은 `EvidenceRef`를 사용한다.
- chat은 source unit이나 retrieval 후보를 새로 꾸미지 않는다. 03에서 만들어진 accepted evidence와 state를 소비한다.
- accepted evidence가 없는 값을 말할 때는 현재 등록된 자료에서 근거를 찾지 못했다는 식으로 원본 범위를 드러낸다.
- `/api/questions`의 기본 product 응답은 `answer`를 중심으로 둔다. retrieval smoke용 excerpt나 raw fact candidate/debug reason을 사용자-facing 응답처럼 함께 노출하지 않는다.

## Non-goals

- 긴 대화 기억.
- 모든 질문 의도 분류.
- 답변 문장 스타일 고도화.
- 카드 초안 생성은 05에서 다룬다.
- Agoda HTML 메일 본문까지 자동으로 찾아 답변하기.

## 현재 코드에서 볼 곳

- `apps/server/schemas/answers.py`: `ChatAnswer`와 항목별 상태/근거 응답 계약.
- `apps/server/answers/checkin.py`: 03의 fact candidate를 사용자-facing answer item으로 바꾼다.
- `apps/server/api/routes/questions.py`: `/api/questions`가 ready material, fact candidate, `ChatAnswer`를 연결한다.
- `apps/client/App.tsx`: 질문 응답의 `answer`를 assistant message에 싣는다.
- `apps/client/components/ChatWorkspace.tsx`: 답변 항목, 상태 pill, inline evidence snippet을 렌더링한다.
- `apps/client/types.ts`: client의 `QuestionResponse`와 `ChatAnswer` 타입.

## 현재 구현 관찰

- 예약 확정서 제시 fact가 `supported`이면 답변 항목은 `근거 있음`과 함께 source unit 원문에서 좁힌 evidence snippet을 보여준다.
- 체크인 시작 시각 fact가 `missing`이면 값을 만들지 않고 현재 등록된 자료에서 확인하지 못했다고 표현한다.
- LLM/proposer가 예약 확정서 근거 문장을 의역해도 source unit 전체를 evidence로 보여주지 않고, 예약 확정서 제시 주변 문장으로 좁힌다.
- 현재 PDF에는 체크인 날짜는 있지만 체크인 시작 시각은 없어 `근거 부족`이 맞다. companion source가 추가되면 같은 `ChatAnswer` 계약 안에서 `근거 있음`으로 바뀔 수 있다.
- 기본 `/api/questions` 응답은 `answer` 중심이고, 02의 `excerpt`와 03의 raw `facts`는 product 응답에 함께 싣지 않는다.

## 이번 AC

1. 사용자가 질문하면 assistant 답변이 나온다.
2. 답변에 체크인 시 예약 확정서 제시 안내와 `근거 있음`이 보인다.
3. 답변에 체크인 시작 시각 `근거 부족`이 보인다.
4. PDF 근거 snippet을 답변 안에서 확인할 수 있다.
5. 답변은 등록되지 않은 companion source 값을 PDF 근거처럼 말하지 않는다.

## 남은 판단

- 근거를 항상 펼쳐 보일지, 접었다 펼치는 UI로 둘지.
- 한 질문 안에서 두 항목을 한 답변 카드로 보여줄지, 항목별 작은 블록으로 나눌지.
- `facts[]`, retrieval excerpt, proposer reason 같은 debug/raw 응답을 별도 개발자용 endpoint나 mode로 다시 열지 여부.
