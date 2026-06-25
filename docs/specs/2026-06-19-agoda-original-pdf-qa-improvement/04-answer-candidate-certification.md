# Answer candidate certification vertical

작성일: 2026-06-25

상태: draft sub-spec. source unit 구조화와 측정 preflight 이후, LLM이 만든 답변 후보를 final answer로 바로 믿지 않고 코드가 다시 인증해 최종 evidence state를 정하게 하는 첫 product safety vertical이다.

이 문서의 중심은 질문 분해가 아니다. 먼저 한 LLM 호출이 `body`·`value`·`evidence_state`·`source_unit_id`·`evidence_snippet`을 동시에 내고, 코드가 그 `evidence_state`를 거의 그대로 통과시키는 self-certification 구조를 끊는다. 질문을 여러 evidence requirement로 나누는 일은 `05-question-decomposition-requirements.md`에서 다룬다.

## 사용자 장면

사용자가 예약 확인서에 대해 묻는다.

예:

- "NonSmoke, LargeBed는 확정된 조건이야?"
- "취소하거나 노쇼하면 어떻게 돼?"
- "현장에서 추가로 내야 하는 비용이 있어?"

제품은 근거가 있는 값은 버리지 않되, 그 값이 사용자 행동을 바꿀 만큼 확정된 사실인지 따로 판단해야 한다. 특히 P1-01 특별 요청 질문에서 `NonSmoke,LargeBed` 값은 찾았지만 특별 요청 caveat가 함께 보이면 답은 `missing`이 아니라 `needs_review`여야 한다.

## Product 흐름

```text
사용자 질문
-> source unit 후보와 metadata/kind를 포함한 LLM 입력
-> LLM answer candidate(body/value/state/evidence refs)
-> code certification(candidate state 재판정)
-> final ChatAnswerItem
-> 사용자에게 보이는 QA 결과
```

이번 slice는 candidate 생성 이후 final projection 사이에 certification 단계를 만든다. LLM은 여전히 질문 해석과 후보 답변 조립을 맡지만, final `supported` 여부는 코드 계약이 소유한다.

## 개선 기준

LLM payload의 `evidence_state`는 final state가 아니라 후보 state다. 코드가 최소한 아래를 다시 본 뒤 final state를 정한다.

- 후보가 인용한 source unit과 snippet이 실제로 있는가
- 후보가 사용한 source unit의 `kind` 또는 의미 metadata가 claim을 뒷받침할 수 있는 종류인가
- 값만 있는 근거와 조건/caveat 근거를 구분했는가
- 위험한 확정 claim이 조건/caveat 근거 없이 `supported`로 올라가고 있지 않은가

certification은 단어 맞추기 규칙이 아니다. `"확정"` 같은 답변 단어를 찾으면 강등하는 방식은 다음 자료에서 무너진다. 기준은 source unit의 의미 종류와 evidence set이다. 예를 들어 특별 요청은 요청값 source unit만으로 `supported`가 될 수 없고, 확정 여부 또는 숙소 확인 필요 문맥을 담은 조건/caveat kind 근거가 함께 있어야 한다.

## Source unit kind 전달

현재 답변 프롬프트는 `source_unit_id`, `locator`, `text`만 직렬화하고 source unit metadata를 버린다. 이러면 retrieval과 observation에는 살아 있는 `kind`가 LLM 입력에서만 사라진다.

첫 구현은 source unit의 의미 구분을 프롬프트 입력까지 보존한다.

- `kind`, `structural_kind`, `source_text_role`처럼 이미 관측 record에 드러나는 metadata를 answer composer source block에 포함한다.
- metadata는 답을 만드는 하드코딩 값이 아니라, 후보가 어떤 종류의 근거를 보고 있는지 드러내는 입력 신호다.
- metadata field name은 현재 source unit 모델과 observation에 이미 존재하는 값을 우선한다.
- product response body에는 이 debug metadata를 그대로 추가하지 않는다.

## Certification 기준

`supported`는 evidence snippet과 source reference가 있을 때만 가능하다. 하지만 snippet이 source unit text 안에 있다는 것만으로 충분하지 않다.

항목별 상태는 최소한 아래를 구분해야 한다.

- 근거 종류와 snippet이 claim을 사용자-facing 사실로 말하기에 충분하다: `supported`
- 관련 값이나 단서는 있지만 확정성, 조건, 적용 범위가 부족하다: `needs_review`
- 필요한 근거 후보가 없다: `missing`

특히 아래 유형은 조건/caveat 종류 근거를 함께 요구한다.

- 특별 요청: 요청 내용과 확정 여부 또는 숙소 확인 필요 문맥
- 취소/노쇼: 정책 조건, 기간, 수수료/환불 또는 노쇼 적용 문맥
- 현장 추가 비용: 비용 종류, 발생 조건, 현장 지불/숙소 확인 문맥
- 체크인 시간: 날짜와 시간의 출처가 다르면 추정하지 않는 문맥
- 준비물/현장 확인: 사용자가 해야 할 행동과 필요한 근거 문맥

source unit이 값을 담고 있어도 조건 문맥이 빠져 있으면 supported가 아니라 needs_review가 될 수 있어야 한다. 특별 요청처럼 value-only 후보와 조건/caveat 후보가 함께 있을 때는 값을 버리지 않고, final answer를 `needs_review`로 내려 사용자가 확인할 수 있게 한다.

## Answer assembly

LLM은 넓은 문서에서 답을 새로 찾는 역할이 아니다. 앞 단계가 찾아온 후보와 certification 결과를 바탕으로 사용자에게 읽기 좋은 답변을 조립한다.

좋은 조립:

- 찾은 값과 확인이 필요한 이유를 함께 말한다.
- supported 항목에는 짧은 근거를 붙인다.
- needs_review 항목은 "확정"처럼 말하지 않는다.
- missing 항목은 값 자체를 찾지 못한 경우에만 쓴다.

나쁜 조립:

- LLM이 `supported`라고 냈다는 이유만으로 final supported로 만든다.
- 요청값만 보고 특별 요청을 확정 조건처럼 말한다.
- 관련 값을 찾았는데 certification 실패를 전부 missing으로 내려 값을 버린다.
- prompt 문구만 늘리고 final state 계약은 그대로 둔다.

## 구현 규칙

- LLM output은 final answer가 아니라 answer candidate다.
- answer composer가 product state를 단독으로 확정하지 않게 한다.
- evidence snippet이 없거나 source reference가 없으면 supported가 될 수 없다.
- source unit kind/metadata를 LLM 입력과 certification에서 사용할 수 있게 보존한다.
- `"확정"` 같은 특정 단어 탐지로 상태를 정하지 않는다.
- P1-01처럼 값은 찾았지만 조건/caveat 때문에 확정할 수 없는 경우는 `missing`이 아니라 `needs_review`로 둔다.
- 위험한 여행 정보는 supported를 늘리는 것보다 근거 부족한 supported를 줄이는 것을 우선한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. LLM이 `evidence_state: supported`를 반환해도 code certification이 final state를 다시 정할 수 있다.
2. answer composer source block은 source unit의 의미 구분을 담은 metadata/kind를 보존한다.
3. P1-01 특별 요청 케이스는 요청값만으로 확정 supported 처리되지 않는다.
4. P1-01에서 요청값을 찾은 경우 final state는 값을 버리는 `missing`이 아니라 `needs_review`가 될 수 있다.
5. certification은 특정 답변 단어 하드코딩이 아니라 source unit kind/metadata와 grounded evidence set을 기준으로 한다.
6. 같은 원문 PDF 질문셋을 실행했을 때 report에서 LLM candidate와 final answer/evidence state 차이를 before/after로 읽을 수 있다.

## 확인 방법

1. 측정 preflight 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 P1-01 특별 요청을 우선 확인한다.
3. LLM candidate가 supported를 제안했더라도 final state가 code certification을 거쳤는지 확인한다.
4. P1-01에서 `NonSmoke,LargeBed` value-only evidence가 확정 supported로 처리되지 않는지 확인한다.
5. 관련 값을 찾았는데 조건/caveat 때문에 확정할 수 없는 경우 `needs_review`로 남는지 확인한다.
6. supported가 늘었는지만 보지 말고, 근거 부족한 supported가 줄었는지 확인한다.
7. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- compound question 전체 분해를 이 slice에 넣지 않는다. 그 작업은 `05-question-decomposition-requirements.md`에서 다룬다.
- 하위 요청별 retrieval coverage 전체를 이 slice에 넣지 않는다. 그 작업은 `06-subrequest-retrieval-coverage.md`에서 다룬다.
- lexical/kind/adjacent context 후보 보강을 이 slice의 성공 기준으로 삼지 않는다.
- UI 카드 승격이나 human review workflow 전체를 이 slice에 넣지 않는다.
- release gate나 점수 threshold를 확정하지 않는다.
- 원문 PDF 외 다른 업체별 fixture 일반화 평가를 이 slice의 필수 완료 기준으로 삼지 않는다.
- prompt 문장 품질만으로 개선 성공을 선언하지 않는다.
