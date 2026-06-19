# State validation and answer assembly

작성일: 2026-06-19

상태: draft sub-spec. source unit 구조화, question decomposition, subrequest retrieval 이후에도 남는 위험한 supported와 반쪽 답변을 줄이기 위한 product slice다.

이 문서의 중심은 prompt polish가 아니다. 값과 조건 문맥을 함께 검증하고, LLM의 역할을 찾아온 근거를 사용자에게 설명하는 조립자로 제한하는 것이다.

## 사용자 장면

사용자는 예약 확인서에서 행동에 영향을 주는 정보를 묻는다.

예:

- 특별 요청이 확정됐는지
- 취소하거나 노쇼하면 어떻게 되는지
- 현장에서 추가 비용을 내야 하는지
- 체크인 날짜와 시간이 충분히 확인됐는지

이 질문들은 값 하나만 맞아도 위험할 수 있다. 요청과 확정, 비용과 발생 조건, 정책명과 적용 조건을 함께 봐야 한다.

## Product 흐름

```text
subrequest별 후보 source unit
-> evidence sufficiency check
-> 항목별 state validation
-> answer assembly
-> 사용자에게 보이는 QA 결과
```

이번 slice는 `evidence sufficiency check`, `항목별 state validation`, `answer assembly`의 경계를 다룬다.

## 상태 기준

`supported`는 evidence snippet과 source reference가 있을 때만 가능하다. 하지만 snippet이 source unit text 안에 있다는 것만으로 충분하지 않다.

항목별 상태는 최소한 아래를 구분해야 한다.

- 값과 조건 문맥이 함께 있어 행동 판단에 충분하다: `supported`
- 원문에 관련 단서는 있지만 확정/조건/적용 범위가 부족하다: `needs_review`
- 필요한 근거 후보가 없다: `missing`

위 이름은 현재 product model에 맞춰 조정할 수 있다. 중요한 것은 값만 보고 supported를 확정하지 않는 것이다.

## Evidence sufficiency

특히 아래 유형은 조건 문맥을 함께 요구한다.

- 특별 요청: 요청 내용과 확정 여부 또는 숙소 확인 필요 문맥
- 취소/노쇼: 정책 조건, 기간, 수수료/환불 또는 노쇼 적용 문맥
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 지불/숙소 확인 문맥
- 체크인 시간: 날짜와 시간의 출처가 다르면 추정하지 않는 문맥
- 준비물/현장 확인: 사용자가 해야 할 행동과 필요한 근거 문맥

source unit이 값을 담고 있어도 조건 문맥이 빠져 있으면 supported가 아니라 needs_review가 될 수 있어야 한다.

## Answer assembly

LLM은 넓은 문서에서 답을 새로 찾는 역할이 아니다. 앞 단계가 찾아온 후보와 state validation 결과를 바탕으로 사용자에게 읽기 좋은 답변을 조립한다.

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

- answer composer가 product state를 단독으로 확정하지 않게 한다.
- prompt 수정은 source unit, subrequest, retrieval 후보가 준비된 뒤 적용한다.
- evidence snippet이 없거나 source reference가 없으면 supported가 될 수 없다.
- 값과 조건 문맥이 분리되어 있으면 같은 항목의 evidence set으로 묶였는지 확인한다.
- 위험한 여행 정보는 supported를 늘리는 것보다 근거 부족한 supported를 줄이는 것을 우선한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. 특별 요청은 요청 내용만으로 확정된 것처럼 supported 처리되지 않는다.
2. 취소/노쇼 질문은 취소 조건과 노쇼 조건을 분리해 상태를 판단한다.
3. 현장 추가 비용은 비용 가능성과 발생 조건/확인 필요 문맥을 함께 본다.
4. 체크인/체크아웃처럼 여러 하위 요청이 있는 질문은 일부만 찾았을 때 전체를 supported로 만들지 않는다.
5. answer composer는 찾아온 후보 밖의 값을 추정하지 않는다.
6. 같은 원문 PDF 질문셋을 실행했을 때 report에서 항목별 state와 evidence path를 before/after로 비교할 수 있다.

## 확인 방법

1. subrequest retrieval 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 특별 요청, 취소/노쇼, 현장 추가 비용 질문을 우선 확인한다.
3. supported가 늘었는지만 보지 말고, 근거 부족한 supported가 줄었는지 확인한다.
4. 항목별 evidence snippet과 source reference가 product response의 상태와 일치하는지 확인한다.
5. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- UI 카드 승격이나 human review workflow 전체를 이 slice에 넣지 않는다.
- release gate나 점수 threshold를 확정하지 않는다.
- 원문 PDF 외 다른 업체별 fixture 일반화 평가를 이 slice의 필수 완료 기준으로 삼지 않는다.
- prompt 문장 품질만으로 개선 성공을 선언하지 않는다.
