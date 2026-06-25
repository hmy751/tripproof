# Subrequest retrieval coverage

작성일: 2026-06-24

상태: draft sub-spec. answer candidate certification과 question decomposition 이후, 각 evidence requirement가 필요한 source unit 후보를 더 안정적으로 받도록 retrieval coverage를 개선하기 위한 product slice다.

이 문서의 중심은 retrieval 점수 자체가 아니다. `05-question-decomposition-requirements.md`의 requirement와 `04-answer-candidate-certification.md`의 certification이 필요한 source unit 후보를 하위 요청별로 받을 수 있는지, 후보가 없을 때 어디서 빠졌는지 읽을 수 있게 만드는 것이다.

## 사용자 장면

사용자가 하나의 질문을 던졌고, 제품은 이를 여러 evidence requirement로 나눴다. 이제 각 requirement가 필요한 source unit 후보를 받아야 한다.

예:

```text
질문: 예약된 객실과 인원은 어떻게 돼?
requirement A: 객실 타입을 찾는다
requirement B: 객실 수를 찾는다
requirement C: 성인 수를 찾는다
requirement D: 아동 수를 찾는다
```

네 requirement가 모두 같은 큰 source unit 하나만 받는다면 retrieval은 여전히 certification을 충분히 돕지 못한 것이다.

## Product 흐름

```text
evidence requirement 목록
-> requirement별 retrieval query
-> source unit 후보
-> candidate coverage 판단
-> answer candidate 생성
-> code certification
-> 항목별 answer/evidence/status
```

이번 slice는 `requirement별 retrieval query`, `source unit 후보`, `candidate coverage 판단`까지의 계약을 다룬다. 최종 supported/needs_review/missing 정책은 `04`의 certification 계약을 따른다.

## 개선 기준

retrieval은 질문 전체에 대한 top-k 한 번으로 끝나면 안 된다. 하위 requirement마다 필요한 source unit 후보를 별도로 찾고, 후보가 없을 때 원인을 구분할 수 있어야 한다.

기본 후보 경로:

- vector search 후보

보조 후보 경로:

- source unit kind/semantic hint 기반 후보
- 라벨/동의어 기반 lexical recall 후보
- 같은 heading, row, table-like group 안의 인접 context

이 경로들은 답변 전략 목록이 아니라 requirement별 candidate discovery와 coverage를 관찰하기 위한 경로다. 기본 경로는 현재 사용자가 넣은 자료에서 생성된 source unit을 대상으로 requirement query를 검색하는 것이며, lexical/kind/인접 context는 후보를 보완하거나 누락 원인을 설명하는 보조 경로로만 둔다.

lexical recall은 답을 만드는 규칙이 아니다. vector search가 놓칠 수 있는 라벨-값, 짧은 정책 제목, 비용 이름을 현재 source unit 후보군 안에서 다시 찾는 보조 장치다. 업체명, question id, eval expected cue, run artifact, source unit id를 미리 매핑해 후보를 꽂지 않는다. lexical/kind hit는 답변 값이나 supported 상태를 직접 만들 수 없고, candidate는 `04`의 certification을 통과하기 전까지 근거가 아니다.

## Candidate coverage

각 requirement는 answer composer로 넘어가기 전에 최소한 아래를 관찰할 수 있어야 한다.

- 후보가 있는가
- 후보가 어떤 source unit locator/kind에서 왔는가
- 후보가 값만 담는가, 조건/caveat 문맥도 담는가
- 후보가 vector, lexical, kind hint, 인접 context 중 어떤 경로로 들어왔는가
- 후보가 없으면 source unit 부재인지, retrieval miss인지, decomposition miss인지 구분 가능한가

정확한 field name은 구현 시 현재 observation/report 모델에 맞춘다. 다만 product response body에 이 정보를 그대로 노출하지 않는다.

## 구현 규칙

- product code는 eval dataset, expected cue, run artifact를 읽지 않는다.
- retrieval query는 requirement intent와 source unit metadata를 사용하되, 질문셋 정답 문자열을 직접 주입하지 않는다.
- lexical rule은 후보 recall 보조로만 사용한다. 답변 값, evidence state, supported 판단을 직접 만들면 안 된다.
- source unit이 너무 큰 상태에서 rerank/model 변경만으로 해결하려 하지 않는다.
- 후보가 없으면 answer composer에게 넓은 문서 전체를 넘겨 답을 기대하지 않는다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

1. compound question은 requirement별 retrieval candidate를 가진다.
2. 체크인/체크아웃, 객실/인원, 취소/노쇼 질문에서 후보 source unit 조합이 requirement별로 달라진다.
3. 후보는 source unit locator와 kind를 유지한다.
4. 후보 경로가 vector-only인지 lexical/kind/context 보조를 거쳤는지 report에서 확인할 수 있다.
5. 후보가 없을 때 missing 원인이 source unit 부재, retrieval miss, decomposition miss 중 어디에 가까운지 사람이 읽을 수 있다.
6. lexical recall이 답변이나 supported 상태를 직접 만들지 않는다.
7. 통과 판단은 candidate 필드 증가가 아니라 answer/evidence path 변화와 certification 결과 변화로 한다.

## 확인 방법

1. `04` certification과 `05` decomposition 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 각 requirement의 candidate 목록을 확인한다.
3. 모든 질문이 같은 두 source unit 후보에 기대는지, 아니면 requirement별 후보가 달라졌는지 비교한다.
4. 후보가 있는 requirement와 없는 requirement를 구분하고, 없는 경우 원인을 기록한다.
5. candidate 증가만 보지 말고 answer/evidence path가 실제로 달라졌는지 확인한다.
6. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 답변 문장 품질 개선을 이 slice에 넣지 않는다.
- supported/needs_review/missing 최종 상태 정책을 이 slice에서 새로 확정하지 않는다.
- embedding model 교체나 reranker 도입을 첫 해법으로 삼지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
