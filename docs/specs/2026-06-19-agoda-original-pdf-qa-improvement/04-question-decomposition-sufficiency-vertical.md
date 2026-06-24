# Question decomposition and sufficiency vertical

작성일: 2026-06-24

상태: draft sub-spec. source unit 구조화와 측정 preflight 이후, 한 질문 안의 여러 정보 요청을 하위 evidence requirement로 나누고 value-only evidence가 supported로 확정되지 않게 하는 첫 product safety vertical이다.

이 문서의 중심은 분해 자체가 아니다. 사용자 질문을 근거 요구 단위로 나누고, 값과 조건 문맥이 충분히 묶였을 때만 supported가 될 수 있게 만드는 것이다.

## 사용자 장면

사용자가 예약 확인서에 대해 자연스러운 질문 하나를 던진다.

예:

- "체크인하고 체크아웃하는 날짜가 언제야?"
- "예약된 객실과 인원은 어떻게 돼?"
- "취소하거나 노쇼하면 어떻게 돼?"
- "NonSmoke, LargeBed는 확정된 조건이야?"

사용자는 질문을 여러 개로 나누어 쓰지 않았지만, 제품은 필요한 하위 evidence requirement를 분리하고 각 requirement의 충분성을 판단해야 한다.

## Product 흐름

```text
사용자 질문
-> rule/intent 기반 question decomposition
-> evidence requirement 목록
-> 현재 source unit 후보와 grounding 결과
-> evidence sufficiency check
-> 항목별 answer/evidence/status
-> 사용자에게 보이는 QA 결과
```

이번 slice는 decomposition과 sufficiency check를 한 vertical로 다룬다. 후보 recall을 넓히는 별도 retrieval coverage 개선은 `05`에서 다룬다.

## 개선 기준

하나의 질문이 하나의 answer item을 의미한다고 가정하지 않는다. 질문이 여러 필드, 여러 조건, 여러 행동 판단을 요구하면 하위 evidence requirement로 나눈다.

대표 requirement:

- 체크인/체크아웃 날짜: arrival date와 departure date를 분리한다.
- 객실/인원: 객실 타입, 객실 수, 성인 수, 아동 수를 분리한다.
- 취소/노쇼: 취소 조건, 취소 수수료/환불, 노쇼 조건을 분리한다.
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 지불/확인 필요 여부를 분리한다.
- 특별 요청: 요청 내용과 확정 여부 또는 숙소 확인 필요 문맥을 함께 요구한다.

분해 결과는 답변이 아니라 evidence requirement다. 각 requirement는 "무엇을 찾아야 하고, 어떤 조건 문맥이 있어야 supported가 가능한가"를 나타내야 하며, 원문에 없는 값을 만들어서는 안 된다.

## 분해 방식

첫 구현은 별도 LLM planner가 아니라 얇은 rule/intent 기반 분해로 둔다. 목적은 답을 예측하는 것이 아니라 retrieval과 sufficiency가 읽을 수 있는 requirement를 만드는 것이다.

- 업체명, question id, eval expected cue, run artifact를 product decomposition에 넣지 않는다.
- Agoda 전용 질문 template로 닫지 않는다.
- 단일 요청 질문을 억지로 여러 개로 쪼개지 않는다.
- 분해가 애매하면 원 질문을 하나의 requirement로 유지하고 이후 retrieval/answer 단계에서 상태를 판단한다.
- 별도 LLM planner, multi-agent planner, semantic judge는 이번 slice의 필수 구현이 아니다.

## Sufficiency 기준

`supported`는 evidence snippet과 source reference가 있을 때만 가능하다. 하지만 snippet이 source unit text 안에 있다는 것만으로 충분하지 않다.

항목별 상태는 최소한 아래를 구분해야 한다.

- 값과 조건 문맥이 함께 있어 행동 판단에 충분하다: `supported`
- 원문에 관련 단서는 있지만 확정/조건/적용 범위가 부족하다: `needs_review`
- 필요한 근거 후보가 없다: `missing`

특히 아래 유형은 조건 문맥을 함께 요구한다.

- 특별 요청: 요청 내용과 확정 여부 또는 숙소 확인 필요 문맥
- 취소/노쇼: 정책 조건, 기간, 수수료/환불 또는 노쇼 적용 문맥
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 지불/숙소 확인 문맥
- 체크인 시간: 날짜와 시간의 출처가 다르면 추정하지 않는 문맥
- 준비물/현장 확인: 사용자가 해야 할 행동과 필요한 근거 문맥

source unit이 값을 담고 있어도 조건 문맥이 빠져 있으면 supported가 아니라 needs_review가 될 수 있어야 한다. 특별 요청처럼 value-only 후보와 조건 문맥 후보가 따로 있을 때는 같은 requirement의 evidence set으로 묶였는지 확인한다.

## Answer assembly

LLM은 넓은 문서에서 답을 새로 찾는 역할이 아니다. 앞 단계가 찾아온 후보와 sufficiency 결과를 바탕으로 사용자에게 읽기 좋은 답변을 조립한다.

좋은 조립:

- 항목별로 찾은 것과 못 찾은 것을 구분한다.
- supported 항목에는 짧은 근거를 붙인다.
- needs_review 항목은 "확정"처럼 말하지 않는다.
- missing 항목은 원문에 없는지, retrieval에서 못 찾은 것인지 구분 가능한 내부 reason을 남긴다.

나쁜 조립:

- 일부 항목만 찾았는데 전체 질문을 supported로 만든다.
- 특별 요청을 확정 조건처럼 말한다.
- 취소/노쇼 정책의 일부 문장만 보고 전체 정책을 단정한다.
- prompt로 자연스러운 답변을 만들면서 evidence state를 느슨하게 만든다.

## 구현 규칙

- decomposition은 값을 만들지 않는다. 값은 source unit retrieval과 evidence path를 거쳐야 한다.
- answer composer가 product state를 단독으로 확정하지 않게 한다.
- evidence snippet이 없거나 source reference가 없으면 supported가 될 수 없다.
- 값과 조건 문맥이 분리되어 있으면 같은 항목의 evidence set으로 묶였는지 확인한다.
- 위험한 여행 정보는 supported를 늘리는 것보다 근거 부족한 supported를 줄이는 것을 우선한다.
- prompt 수정은 source unit, requirement, sufficiency 계약이 준비된 뒤 적용한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. 체크인/체크아웃 질문은 최소 두 개의 하위 evidence requirement로 나뉜다.
2. 객실/인원 질문은 객실 타입, 객실 수, 성인 수, 아동 수를 별도 requirement로 다룰 수 있다.
3. 취소/노쇼 질문은 취소 조건과 노쇼 조건을 분리해 상태를 판단한다.
4. 특별 요청 질문은 요청 내용만으로 확정된 것처럼 supported 처리되지 않는다.
5. 체크인/체크아웃, 객실/인원처럼 여러 하위 요청이 있는 질문은 일부만 찾았을 때 전체를 supported로 만들지 않는다.
6. answer composer는 찾아온 후보 밖의 값을 추정하지 않는다.
7. 같은 원문 PDF 질문셋을 실행했을 때 report에서 requirement, 항목별 state, evidence path를 before/after로 비교할 수 있다.

## 확인 방법

1. 측정 preflight 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 P0-05 객실/인원, P0-06 취소/노쇼, P1-01 특별 요청을 우선 확인한다.
3. 각 requirement가 answer value가 아니라 evidence need로 남아 있는지 확인한다.
4. supported가 늘었는지만 보지 말고, 근거 부족한 supported가 줄었는지 확인한다.
5. P1-01에서 `NonSmoke,LargeBed` value-only evidence가 확정 supported로 처리되지 않는지 확인한다.
6. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 하위 요청별 retrieval coverage 전체를 이 slice에 넣지 않는다.
- lexical/kind/adjacent context 후보 보강을 이 slice의 성공 기준으로 삼지 않는다.
- UI 카드 승격이나 human review workflow 전체를 이 slice에 넣지 않는다.
- release gate나 점수 threshold를 확정하지 않는다.
- 원문 PDF 외 다른 업체별 fixture 일반화 평가를 이 slice의 필수 완료 기준으로 삼지 않는다.
- prompt 문장 품질만으로 개선 성공을 선언하지 않는다.
