# Question decomposition

작성일: 2026-06-19

상태: draft sub-spec. source unit 구조화 이후에도 한 질문 안의 여러 정보 요청을 놓치는 실패를 줄이기 위한 다음 product 개선 slice다.

이 문서의 중심은 답을 만드는 것이 아니다. 사용자 질문을 근거를 찾아야 하는 하위 정보 요청으로 나누고, 일부만 찾은 답을 전체 supported로 뭉개지 않게 만드는 것이다.

## 사용자 장면

사용자가 예약 확인서에 대해 자연스러운 질문 하나를 던진다.

예:

- "체크인하고 체크아웃하는 날짜가 언제야?"
- "예약된 객실과 인원은 어떻게 돼?"
- "취소하거나 노쇼하면 어떻게 돼?"

사용자는 질문을 여러 개로 나누어 쓰지 않았지만, 제품은 필요한 하위 정보 요청을 분리해 각각 근거를 찾을 준비를 해야 한다.

## Product 흐름

```text
사용자 질문
-> question decomposition
-> subrequest 목록
-> subrequest별 retrieval
-> 항목별 answer/evidence/status
-> 사용자에게 보이는 QA 결과
```

이번 slice는 `question decomposition`과 `subrequest 목록`까지의 계약을 다룬다. retrieval, 상태 검증, 답변 조립은 다음 문서에서 이어서 다룬다.

## 개선 기준

하나의 질문이 하나의 answer item을 의미한다고 가정하지 않는다. 질문이 여러 필드, 여러 조건, 여러 행동 판단을 요구하면 하위 요청으로 나눈다.

대표 분해 대상:

- 체크인/체크아웃 날짜: arrival/date와 departure/date를 분리한다.
- 객실/인원: 객실 타입, 객실 수, 성인 수, 아동 수를 분리한다.
- 취소/노쇼: 취소 조건, 취소 수수료/환불, 노쇼 조건을 분리한다.
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 확인 필요 여부를 분리한다.
- 특별 요청: 요청 내용과 확정 여부/숙소 확인 필요 문맥을 분리한다.

분해 결과는 답변이 아니라 retrieval 의도다. 각 subrequest는 "무엇을 찾아야 하는가"를 나타내야 하며, 원문에 없는 값을 만들어서는 안 된다.

## Subrequest 계약

정확한 field name은 구현 시 현재 자료 모델에 맞춰 정한다. 다만 최소한 아래 정보를 표현할 수 있어야 한다.

- 원래 사용자 질문과 연결되는 parent reference
- 하위 요청의 사용자-facing label
- retrieval에 사용할 짧은 query 또는 intent
- 기대하는 source unit 유형 hint
- 답변에 필요한 context 조건

예시:

```text
parent question: 체크인하고 체크아웃하는 날짜가 언제야?
subrequests:
- check-in date / arrival date를 찾는다
- check-out date / departure date를 찾는다
```

```text
parent question: 취소하거나 노쇼하면 어떻게 돼?
subrequests:
- cancellation policy를 찾는다
- no-show policy를 찾는다
- 환불/수수료 조건을 찾는다
```

## 구현 규칙

- 질문셋의 expected answer나 rule check 문구를 product decomposition에 넣지 않는다.
- Agoda 전용 질문 template로 닫지 않는다.
- decomposition은 값을 만들지 않는다. 값은 source unit retrieval과 evidence path를 거쳐야 한다.
- 단일 요청 질문을 억지로 여러 개로 쪼개지 않는다.
- 분해 실패가 곧 missing 답변이 되면 안 된다. 분해가 애매하면 원 질문을 하나의 subrequest로 유지하고 이후 retrieval/answer 단계에서 상태를 판단한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. 체크인/체크아웃 질문은 최소 두 개의 하위 요청으로 나뉜다.
2. 객실/인원 질문은 객실 정보와 인원 정보를 별도 하위 요청으로 다룰 수 있다.
3. 취소/노쇼 질문은 취소 조건과 노쇼 조건을 별도 하위 요청으로 다룰 수 있다.
4. 특별 요청 질문은 요청 내용과 확정/숙소 확인 필요 문맥을 별도 하위 요청으로 다룰 수 있다.
5. 하위 요청은 답변 값이나 supported 상태를 직접 만들지 않는다.
6. 같은 원문 PDF 질문셋을 실행했을 때 report에서 한 질문이 어떤 subrequest들로 이어졌는지 확인할 수 있다.

## 확인 방법

1. source unit 구조화 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 compound question을 열어 subrequest 목록이 생겼는지 확인한다.
3. 각 subrequest가 answer value가 아니라 retrieval intent로 남아 있는지 확인한다.
4. 일부 subrequest가 실패해도 전체 질문이 곧바로 supported로 확정되지 않는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 하위 요청별 retrieval ranking 전체를 이 slice에 넣지 않는다.
- 상태 검증 전체를 이 slice에 넣지 않는다.
- 답변 문장 품질이나 prompt polish를 이 slice의 성공 기준으로 삼지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
