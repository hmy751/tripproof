# Source unit structure improvement

작성일: 2026-06-19

상태: draft sub-spec. 원문 PDF baseline에서 확인한 실패를 줄이기 위한 첫 product 개선 slice다.

이 문서의 중심은 runner나 report 필드를 늘리는 것이 아니다. 원문 PDF가 retrieval과 answer evidence로 쓰일 수 있는 source unit으로 더 잘 들어오게 만드는 것이다.

## 사용자 장면

개발자가 원문 Agoda PDF와 8개 질문셋을 돌린다. baseline report에서 필요한 정보가 큰 page-like 덩어리에 묻히거나, 질문에 필요한 조건 문맥이 candidate로 잘 올라오지 않는 것을 확인한다.

그 다음 source unit 생성 방식을 개선하고, 같은 원문 PDF와 같은 질문셋, 같은 production-like runtime 조건으로 다시 실행한다. before/after report에서 source unit kind, locator, retrieval candidate, answer/evidence가 어떻게 달라졌는지 확인한다.

Before 기준 artifact:

- `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/`
- `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/report.html`
- `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/run.json`

## Product 흐름

```text
원문 PDF
-> text/layout extraction
-> source unit 생성
-> retrieval candidate
-> answer/evidence
-> 사용자에게 보이는 QA 결과
```

이번 slice는 `source unit 생성`을 개선한다. eval runner, report, `run.json`은 개선 효과를 보기 위한 소비자다.

## 개선 기준

원문 PDF는 page-length 덩어리 몇 개로만 남으면 안 된다. 아래처럼 여행 예약 문서에서 반복되는 의미 단위가 source unit으로 드러나야 한다.

- 체크인 준비물, 예약 확정서, 신분증, 결제 카드처럼 사용자가 현장에서 해야 할 일
- 체크인/체크아웃, 객실, 인원처럼 라벨과 값이 붙어 있는 정보
- 취소, 노쇼, 환불, 현장 결제처럼 조건이 중요한 정책 문단
- 추가 비용, 세금, 보증금, 숙소에서 확인해야 하는 비용 안내
- 특별 요청, 주의사항, 숙소 확인 필요 항목

source unit은 최소한 사람이 report에서 위치와 유형을 추적할 수 있어야 한다.

- `locator`: page, block, row 등 원문 위치를 다시 찾을 수 있는 정보
- `kind`: label-value, policy, warning, fee, request note 같은 정보 유형
- `char_length`: 너무 큰 덩어리인지 확인하기 위한 길이 단서

정확한 field name과 kind 목록은 구현 시 현재 자료 모델에 맞춰 정한다. 이 문서는 값 목록을 고정하는 것이 아니라, source unit이 질문 가능한 의미 단위가 되어야 한다는 제품 기준을 고정한다.

현재 before baseline의 직접 관찰은 다음과 같다.

- 원문 PDF는 `source_unit_count=2`로만 생성됐다.
- 두 source unit이 전 질문의 retrieval candidate로 반복해서 올라온다.
- 필요한 단서가 candidate context 안에 있어도 answer composer가 일부만 뽑거나 evidence state를 오판한다.

따라서 이 slice의 첫 성공 신호는 답변 문구 개선이 아니라, 질문별 required cue가 더 좁은 source unit과 locator로 추적되는 것이다.

## 구현 규칙

- Agoda 전용 parser를 만들지 않는다.
- 특정 질문 문구를 보고 답을 만드는 rule을 넣지 않는다.
- lexical rule은 구조 감지나 후보 recall 보조로 사용할 수 있지만, product answer를 직접 만들면 안 된다.
- 값과 조건 문맥을 분리해서 위험한 supported 상태를 만들지 않는다.
- source unit의 granularity를 줄이더라도 원문 locator와 evidence snippet을 잃지 않는다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. 원문 PDF에서 생성된 source unit은 page-length 덩어리만이 아니라 라벨-값, 정책/주의사항, 비용, 특별 요청 안내 같은 의미 단위를 포함한다.
2. 각 source unit은 locator와 kind를 가져 report에서 원문 근거 위치와 정보 유형을 확인할 수 있다.
3. 같은 8문항을 다시 실행했을 때 report의 `Evidence path`에서 질문별 retrieval candidate가 어떤 source unit을 탔는지 before/after로 비교할 수 있다.
4. 특별 요청, 취소/노쇼, 현장 추가 비용처럼 조건 문맥이 중요한 항목은 값만 보고 supported로 단정하지 않는다.
5. 개선은 sample fixture가 아니라 원문 PDF baseline과 같은 입력으로 확인한다.
6. before/after 비교는 가능한 한 같은 production-like runtime으로 실행한다. deterministic fake embedding, memory-only retrieval, `missing` composer로 만든 run은 구조 smoke로만 보고 원문 PDF QA 개선 근거로 승격하지 않는다.

## 확인 방법

1. `01-original-pdf-observation-baseline.md` 기준으로 production-like before baseline을 만든다.
2. source unit 생성 경로를 개선한다.
3. 같은 원문 PDF와 같은 `questions.json`, 같은 runtime 조건으로 다시 실행한다.
4. before/after report에서 source unit count, kind 분포, candidate locator, answer/evidence 변화를 비교한다.
5. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 질문 분해 전체를 이 slice에 넣지 않는다.
- 하위 요청별 retrieval 전체 개편을 이 slice에 넣지 않는다.
- 상태 검증 전체 개편을 이 slice에 넣지 않는다.
- source unit 구조화가 되기 전에 prompt 수정만으로 점수를 올리려 하지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
