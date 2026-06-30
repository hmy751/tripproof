# Subrequest retrieval coverage

작성일: 2026-06-24
재작성일: 2026-06-29, 순수 coverage로 재범위

상태: draft sub-spec, 아직 미구현. answer certification boundary(`04`) 이후, 하위 요청(role)별로 필요한 source unit 후보를 더 안정적으로 공급하고, 후보가 없을 때 그 원인을 구분하는 retrieval coverage slice다. 아직 코드/eval 없음 — `05` 전용 run은 만들지 않았다(2026-06-29 기준 run 14~19는 전부 `04` certification·`06` relation 작업이다).

이 문서의 중심은 retrieval 점수 자체가 아니다. 하위 요청별로 필요한 source unit 후보를 받을 수 있는지, 후보가 없을 때 어디서 빠졌는지 읽을 수 있는지, 그리고 받은 후보가 값만 담는지 그 값을 좌우할 수 있는 조건 문맥도 담는지를 관찰해 `06`에 넘기는 것이다.

`05`는 후보를 **공급하고 관찰**한다. "그 조건이 이 값을 좌우하는가"의 의미 판단은 하지 않는다 — 그 판단은 `06` 의미 층(LLM/relation extractor)이 역할 구조로 만들고, `04` 코드 certification이 그 역할 구조를 읽어 state를 정한다.

관련 판단:

- `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/04-answer-certification-boundary.md`
- `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/06-evidence-relation-extraction.md`
- `docs/engineering/llm-design.md`

## 책임 범위

`05`가 하는 일과 명시적으로 빠지는 일을 먼저 가른다. 이 경계가 흐려지면 retrieval이 의미 판단을 흉내 내기 시작하고, 같은 자료에서 무너지는 `kind`·page 근접 추정으로 다시 샌다.

`05`가 하는 일:

- 하위 요청(candidate/evidence role)별로 source unit 후보를 더 안정적으로 공급한다.
- 후보가 없을 때 원인을 source unit 부재 / retrieval miss / candidate·relation extraction miss로 구분 가능하게 한다.
- 후보가 retrieval됐는데도 답변이 인용하지 못하거나 다른 질문에 잘못 붙인 경우(selection/인용 실패, 벽②)를 retrieval miss(후보 없음)와 *구분*해 읽는다 — `05`는 이를 구분만 하고 고치진 않는다.
- 받은 후보가 값만 담는지, 그 값을 좌우할 수 있는 caveat 문맥도 담는지를 관찰해 `06`에 넘긴다.
- 후보가 어떤 source unit locator/kind에서, 어떤 경로(vector / lexical / kind hint / 인접 context)로 들어왔는지 보존한다.

`05`가 하지 않는 일:

- "그 조건이 이 값을 좌우하는가"의 판정 — `06` 의미 층의 몫이다. `05`는 조건 문맥이 후보에 함께 있는지만 관찰한다.
- 후보가 값이고 어떤 후보가 caveat인지의 역할 부여 — `06`이 만든다.
- 최종 `supported`/`needs_review`/`missing` 상태 정책 — `04`의 certification 계약이 소유한다.
- 답변 값, evidence state, 사용자-facing 문장 — `05`는 후보만 공급한다.

## P1-01은 coverage 문제가 아니다

이번 묶음의 알려진 위험 실패(P1-01)는 `05`로 풀리지 않는다. 특별 요청 질문에서 `NonSmoke,LargeBed` 값과 "모든 특별 요청은 체크인 때 숙소 사정에 따라 결정"이라는 조건 문맥은 retrieval 후보에 **이미 함께 들어와 있었다.** 못 찾은 게 아니라, 찾은 조건을 안 쓰고 값만으로 "확정"이라 답한 것이다.

따라서 P1-01은 후보를 더 많이 찾는 일(`05`)이 아니라, 이미 들어온 값과 조건의 역할·관계를 만드는 일(`06`)이 binding fix다. `05`는 조건 후보가 실제로 빠지는 compound question — 즉 값 후보는 들어오지만 그 값을 좌우할 수 있는 조건/요청/정책 후보가 role query에서 누락되는 경우 — 를 위한 coverage 일반화다. P1-01은 그 일반화의 동기이지, `05`가 닫을 케이스가 아니다.

## retrieved-but-misused도 coverage 문제가 아니다

`05` 경계와 관련해, `07` A/B run에서 관찰된 또 다른 비-coverage 실패를 여기 정리해 둔다(출처: `eval/runs/question-dataset/25-20260630T-relation-qwen14b-pairwise-A-instrumented/repeat.json` 등 07 묶음). 취소·노쇼 정책은 retrieval 후보에 또렷이 들어와 있었는데도, 노쇼 질문의 답은 그 근거를 인용하지 못해 `missing`으로 떨어졌고, 같은 노쇼 내용이 다른 질문(방 요청)에는 엉뚱하게 새어 들어가기도 했다. 즉 후보를 못 받은 게 아니라, 받은 후보를 답변이 맞는 질문에 붙이지 못한 **selection/인용 문제**다.

이건 `05`가 *고칠* 문제가 아니라(답변 candidate·인용 쪽 몫이다) `05`가 *구분해야* 하는 경우다. coverage 관찰이 "retrieved-but-misused"를 "retrieval miss"와 섞으면, 후보를 더 찾는 헛수고로 빠진다. 그래서 missing 원인 구분(아래 책임 범위)에 "후보는 들어왔으나 답변이 안 썼/잘못 붙였음"을 retrieval miss와 별도로 읽을 수 있어야 한다.

## 사용자 장면

사용자가 하나의 질문을 던졌고, LLM 후보와 `04` certification은 final state를 정하려면 어떤 candidate/evidence role이 충분하거나 부족한지 드러냈다. 이제 검색 단계가 그 role에 필요한 source unit 후보를 더 안정적으로 공급해야 한다.

예:

```text
질문: 예약된 객실과 인원은 어떻게 돼?
candidate/evidence role A: 객실 타입 값을 찾는다
candidate/evidence role B: 객실 수 값을 찾는다
candidate/evidence role C: 성인 수 값을 찾는다
candidate/evidence role D: 아동 수 값을 찾는다
```

네 role이 모두 같은 큰 source unit 하나만 받는다면 retrieval은 여전히 `06`과 certification을 충분히 돕지 못한 것이다.

## Product 흐름

```text
질문 + retrieval 후보 source unit
-> 부족한 candidate/evidence role 확인
-> role별 retrieval query
-> source unit 후보 (값/조건 문맥을 담았는지 관찰)
-> LLM answer candidate
-> 의미 층·관계 추출 (06): 값↔조건 역할 구조
-> code certification (04): 역할 구조 + grounding/value-grounding으로 final state
-> final body rendering
-> 항목별 answer/evidence/status
```

이번 slice는 `role별 retrieval query`, `source unit 후보`, `candidate coverage 판단`까지의 계약을 다룬다. 후보들 사이의 값↔조건 역할 구조는 `06`이, 최종 supported/needs_review/missing 정책은 `04`의 certification 계약이 소유한다.

각 단계는 자기가 받은 것만 가지고 일한다. `05`가 조건 문맥을 담은 후보를 안정적으로 공급해도, "그 조건이 이 값을 좌우한다"는 판정은 `06`이 하고, 그 역할 구조를 읽어 state를 내리는 일은 `04` 코드가 한다.

## 개선 기준

retrieval은 질문 전체에 대한 top-k 한 번으로 끝나면 안 된다. 후보 claim이나 evidence role마다 필요한 source unit 후보를 별도로 찾고, 후보가 없을 때 원인을 구분할 수 있어야 한다.

기본 후보 경로:

- vector search 후보

보조 후보 경로:

- source unit kind/semantic hint 기반 후보
- 라벨/동의어 기반 lexical recall 후보
- 같은 heading, row, table-like group 안의 인접 context

이 경로들은 답변 전략 목록이 아니라 role별 candidate discovery와 coverage를 관찰하기 위한 경로다. 기본 경로는 현재 사용자가 넣은 자료에서 생성된 source unit을 대상으로 role query를 검색하는 것이며, lexical/kind/인접 context는 후보를 보완하거나 누락 원인을 설명하는 보조 경로로만 둔다.

lexical recall은 답을 만드는 규칙이 아니다. vector search가 놓칠 수 있는 라벨-값, 짧은 정책 제목, 비용 이름을 현재 source unit 후보군 안에서 다시 찾는 보조 장치다. 업체명, question id, eval expected cue, run artifact, source unit id를 미리 매핑해 후보를 꽂지 않는다. lexical/kind hit는 답변 값이나 supported 상태를 직접 만들 수 없고, candidate는 `06`의 역할 부여와 `04`의 certification을 통과하기 전까지 근거가 아니다.

조건 문맥 후보도 같은 원칙으로 다룬다. `05`는 값 후보 옆에 조건/요청/정책/주의 후보가 함께 들어왔는지를 보조 경로로 끌어와 관찰하지만, 그 후보에 "이 값을 좌우하는 조건"이라는 역할을 붙이지 않는다 — 그 역할은 `06`이 만든다. `05`가 lexical이나 kind로 "조건이 값에 걸린다"를 직접 판정하면 거울상 함정과 구조 프록시 과잉 강등을 다시 들이는 것이다(`04`의 `구현 범위 재조정`).

## Candidate coverage

각 candidate/evidence role은 `06`과 certification으로 넘어가기 전에 최소한 아래를 관찰할 수 있어야 한다.

- 후보가 있는가
- 후보가 어떤 source unit locator/kind에서 왔는가
- 후보가 값만 담는가, 그 값을 좌우할 수 있는 조건 문맥도 함께 담는가
- 후보가 vector, lexical, kind hint, 인접 context 중 어떤 경로로 들어왔는가
- 후보가 없으면 source unit 부재인지, retrieval miss인지, candidate/relation extraction miss인지 구분 가능한가
- 후보가 retrieval됐는데도 답변이 그 후보를 안 썼거나 다른 질문에 잘못 붙였는가(selection 실패, 벽②) — retrieval miss(후보 없음)와 구분한다

이 관찰은 후보가 값/조건을 담았는지까지만 본다. "그 조건이 이 값을 좌우한다"는 역할 판정은 여기서 하지 않고 `06`에 넘긴다.

정확한 field name은 구현 시 현재 observation/report 모델에 맞춘다. 다만 product response body에 이 정보를 그대로 노출하지 않는다.

## 구현 규칙

- product code는 eval dataset, expected cue, run artifact를 읽지 않는다.
- retrieval query는 candidate/evidence role과 source unit metadata를 사용하되, 질문셋 정답 문자열을 직접 주입하지 않는다.
- lexical rule은 후보 recall 보조로만 사용한다. 답변 값, evidence state, supported 판단, 값↔조건 역할 부여를 직접 만들면 안 된다.
- `05`는 조건 후보가 후보에 들어왔는지만 관찰하고, "조건이 값을 좌우한다"를 `kind`나 page 근접으로 추정하지 않는다(그 판정은 `06`, 근거: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`).
- source unit이 너무 큰 상태에서 rerank/model 변경만으로 해결하려 하지 않는다.
- 후보가 없으면 LLM candidate 단계에 넓은 문서 전체를 넘겨 답을 기대하지 않는다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

> `05`는 후보 공급과 coverage 관찰까지만 강제한다. 후보가 값/조건을 담았는지는 관찰하지만, 그 조건이 값을 좌우하는지의 판정과 그에 따른 상태 강등은 `06` 의미 층과 `04` certification이 소유한다.

1. compound question은 candidate/evidence role별 retrieval candidate를 가진다.
2. 체크인/체크아웃, 객실/인원, 취소/노쇼 질문에서 후보 source unit 조합이 role별로 달라진다.
3. 후보는 source unit locator와 kind를 유지한다.
4. 후보 경로가 vector-only인지 lexical/kind/context 보조를 거쳤는지 report에서 확인할 수 있다.
5. 후보가 없을 때 missing 원인이 source unit 부재, retrieval miss, candidate/relation extraction miss 중 어디에 가까운지 사람이 읽을 수 있다.
6. 값 후보 옆에 조건/요청/정책/주의 문맥 후보가 함께 들어왔는지를 관찰해 `06`에 넘길 수 있다(역할 부여나 좌우 판정은 `05`가 하지 않는다).
7. lexical recall이 답변, supported 상태, 값↔조건 역할을 직접 만들지 않는다.
8. 통과 판단은 candidate 필드 증가가 아니라 answer/evidence path 변화와 certification 결과 변화로 한다.

## 확인 방법

1. `04` vertical 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 각 candidate/evidence role의 candidate 목록을 확인한다.
3. 모든 질문이 같은 두 source unit 후보에 기대는지, 아니면 role별 후보가 달라졌는지 비교한다.
4. 후보가 있는 role과 없는 role을 구분하고, 없는 경우 원인(source unit 부재 / retrieval miss / candidate·relation extraction miss)을 기록한다.
5. 값 후보 옆에 조건 문맥 후보가 함께 들어왔는지 관찰하고, 그 관찰이 `06`에 넘어갈 수 있는 형태인지 본다.
6. candidate 증가만 보지 말고 answer/evidence path가 실제로 달라졌는지 확인한다.
7. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- relation/의미 판단은 `05`가 하지 않고 `06`이 한다. "이 조건이 이 값을 좌우한다 / 필요한 조건 역할이 비었다"의 역할 구조는 `05`의 산출이 아니다.
- 답변 문장 품질 개선을 이 slice에 넣지 않는다.
- supported/needs_review/missing 최종 상태 정책을 이 slice에서 새로 확정하지 않는다.
- code certification의 판단 기준을 lexical recall 결과로 바꾸지 않는다.
- `05`가 lexical/kind/page 근접으로 "조건이 값에 걸린다"를 직접 판정하지 않는다(거울상 함정·구조 프록시 과잉 강등 재발 방지, 근거: `docs/implementation-notes/2026-06-29-certification-keyword-gate-mirror-trap/`, `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`).
- embedding model 교체나 reranker 도입을 첫 해법으로 삼지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
