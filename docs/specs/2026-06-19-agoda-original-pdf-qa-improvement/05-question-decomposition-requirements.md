# Question decomposition requirements

작성일: 2026-06-25

상태: draft sub-spec. answer candidate certification 이후, 하나의 사용자 질문 안에 여러 정보 요청이 섞여 있을 때 이를 하위 evidence requirement로 나누는 product slice다.

이 문서의 중심은 final state 인증이 아니다. `04-answer-candidate-certification.md`가 LLM 후보를 final answer로 인증하는 경계를 먼저 세운 뒤, 이 문서는 사용자의 복합 질문을 답변값이 아니라 근거 요구 단위로 나누는 일을 다룬다.

## 사용자 장면

사용자가 예약 확인서에 대해 자연스러운 질문 하나를 던진다.

예:

- "체크인하고 체크아웃하는 날짜가 언제야?"
- "예약된 객실과 인원은 어떻게 돼?"
- "취소하거나 노쇼하면 어떻게 돼?"
- "현장에서 추가로 내야 하는 비용이 있어?"

사용자는 질문을 여러 개로 나누어 쓰지 않았지만, 제품은 필요한 하위 evidence requirement를 분리하고 각 requirement가 어떤 근거를 필요로 하는지 알아야 한다.

## Product 흐름

```text
사용자 질문
-> rule/intent 기반 question decomposition
-> evidence requirement 목록
-> requirement별 후보 검색 또는 현재 후보 매핑
-> answer candidate 생성
-> code certification
-> 항목별 answer/evidence/status
-> 사용자에게 보이는 QA 결과
```

이번 slice는 decomposition 결과가 answer value가 아니라 evidence requirement로 남게 하는 데 집중한다. requirement별 후보 coverage 개선은 `06-subrequest-retrieval-coverage.md`에서 다룬다.

## 개선 기준

하나의 질문이 하나의 answer item을 의미한다고 가정하지 않는다. 질문이 여러 필드, 여러 조건, 여러 행동 판단을 요구하면 하위 evidence requirement로 나눈다.

대표 requirement:

- 체크인/체크아웃 날짜: arrival date와 departure date를 분리한다.
- 객실/인원: 객실 타입, 객실 수, 성인 수, 아동 수를 분리한다.
- 취소/노쇼: 취소 조건, 취소 수수료/환불, 노쇼 조건을 분리한다.
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 지불/확인 필요 여부를 분리한다.
- 특별 요청: 요청 내용과 확정 여부 또는 숙소 확인 필요 문맥을 함께 요구한다.

분해 결과는 답변이 아니라 evidence requirement다. 각 requirement는 "무엇을 찾아야 하고, 어떤 종류의 근거가 있어야 supported가 가능한가"를 나타내야 하며, 원문에 없는 값을 만들어서는 안 된다.

## 분해 방식

첫 구현은 별도 LLM planner가 아니라 얇은 rule/intent 기반 분해로 둔다. 목적은 답을 예측하는 것이 아니라 retrieval과 certification이 읽을 수 있는 requirement를 만드는 것이다.

- 업체명, question id, eval expected cue, run artifact를 product decomposition에 넣지 않는다.
- Agoda 전용 질문 template로 닫지 않는다.
- 단일 요청 질문을 억지로 여러 개로 쪼개지 않는다.
- 분해가 애매하면 원 질문을 하나의 requirement로 유지하고 이후 retrieval/answer/certification 단계에서 상태를 판단한다.
- 별도 LLM planner, planning layer, semantic judge는 이번 slice의 필수 구현이 아니다.

## Requirement 기준

각 requirement는 최소한 아래를 표현할 수 있어야 한다.

- 찾으려는 항목 또는 행동 판단
- supported가 되기 위해 필요한 source unit kind 또는 의미 종류
- 값 근거와 조건/caveat 근거가 함께 필요한지 여부
- 일부 requirement만 충족됐을 때 전체 질문을 supported로 만들면 안 된다는 제약

특히 아래 유형은 조건/caveat 종류 근거를 함께 요구한다.

- 특별 요청: 요청 내용과 확정 여부 또는 숙소 확인 필요 문맥
- 취소/노쇼: 정책 조건, 기간, 수수료/환불 또는 노쇼 적용 문맥
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 지불/숙소 확인 문맥
- 체크인 시간: 날짜와 시간의 출처가 다르면 추정하지 않는 문맥
- 준비물/현장 확인: 사용자가 해야 할 행동과 필요한 근거 문맥

## Answer assembly

LLM은 넓은 문서에서 답을 새로 찾는 역할이 아니다. 앞 단계가 만든 requirement와 찾아온 후보, 그리고 certification 결과를 바탕으로 사용자에게 읽기 좋은 답변을 조립한다.

좋은 조립:

- 항목별로 찾은 것과 못 찾은 것을 구분한다.
- supported 항목에는 짧은 근거를 붙인다.
- needs_review 항목은 확정처럼 말하지 않는다.
- missing 항목은 원문에 없는지, retrieval에서 못 찾은 것인지 구분 가능한 내부 reason을 남긴다.

나쁜 조립:

- 일부 항목만 찾았는데 전체 질문을 supported로 만든다.
- 취소/노쇼 정책의 일부 문장만 보고 전체 정책을 단정한다.
- requirement 없이 prompt로 자연스러운 답변만 만들면서 evidence state를 느슨하게 만든다.

## 구현 규칙

- decomposition은 값을 만들지 않는다. 값은 source unit retrieval과 evidence path를 거쳐야 한다.
- requirement는 certification이 final state를 판단할 때 읽을 수 있는 계약이어야 한다.
- compound question에서 일부만 찾았을 때 전체를 supported로 만들지 않는다.
- 위험한 여행 정보는 supported를 늘리는 것보다 근거 부족한 supported를 줄이는 것을 우선한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. 체크인/체크아웃 질문은 최소 두 개의 하위 evidence requirement로 나뉜다.
2. 객실/인원 질문은 객실 타입, 객실 수, 성인 수, 아동 수를 별도 requirement로 다룰 수 있다.
3. 취소/노쇼 질문은 취소 조건과 노쇼 조건을 분리해 상태를 판단한다.
4. 특별 요청 질문은 요청값 requirement와 확정/조건 문맥 requirement를 구분할 수 있다.
5. 체크인/체크아웃, 객실/인원처럼 여러 하위 요청이 있는 질문은 일부만 찾았을 때 전체를 supported로 만들지 않는다.
6. answer composer는 찾아온 후보 밖의 값을 추정하지 않는다.
7. 같은 원문 PDF 질문셋을 실행했을 때 report에서 requirement, 항목별 state, evidence path를 before/after로 비교할 수 있다.

## 확인 방법

1. `04` certification 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 P0-05 객실/인원, P0-06 취소/노쇼, P1-01 특별 요청을 우선 확인한다.
3. 각 requirement가 answer value가 아니라 evidence need로 남아 있는지 확인한다.
4. supported가 늘었는지만 보지 말고, 근거 부족한 supported가 줄었는지 확인한다.
5. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- answer candidate certification 구조를 이 slice에 새로 만들지 않는다. 그 경계는 `04-answer-candidate-certification.md`가 소유한다.
- 하위 요청별 retrieval coverage 전체를 이 slice에 넣지 않는다.
- lexical/kind/adjacent context 후보 보강을 이 slice의 성공 기준으로 삼지 않는다.
- UI 카드 승격이나 human review workflow 전체를 이 slice에 넣지 않는다.
- release gate나 점수 threshold를 확정하지 않는다.
- 원문 PDF 외 다른 업체별 fixture 일반화 평가를 이 slice의 필수 완료 기준으로 삼지 않는다.
- prompt 문장 품질만으로 개선 성공을 선언하지 않는다.
