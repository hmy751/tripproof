# Evidence relation extraction (의미 층)

작성일: 2026-06-29

상태: draft sub-spec. answer certification boundary(`04`) 이후, 이미 후보에 들어온 값과 그 값을 조건부로 만드는 caveat 사이의 역할·관계를 만드는 의미 층이다. relation extractor v1(답 호출과 분리된 caveat 검출)은 코드에 있으나(`574dee4`), gemma3:4b에서 무관한 조건을 과잉 부착한다 — per-unit·순서 불변 변형(`118a916`)을 시도했으나 그 과잉을 못 잡아 되돌렸다(`8040665`). 따라서 이 문서의 계약(특히 paraphrase-안정 needs_review)은 아직 달성되지 않은 목표이며, 현재 baseline은 과잉강등을 알려진 한계로 안고 있다. 측정·경계: `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`.

측정 run (2026-06-29, production·seed 20260624; per-unit·순서불변 A/B는 `8040665`로 되돌림):

- inline 검출(`5d1880f`): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/16-evidence-relation-layer-06-after-production/`
- 분리 호출(`574dee4`): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/17-evidence-relation-pass-separated/`
- per-unit B(`118a916`, `mode=pairwise`): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/18-caveat-pairwise-B/`
- 순서불변 A(`118a916`, `mode=order_invariant`): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/19-caveat-order-invariant-A/`
- 질문별 수치·과잉 부착 caveat 발췌: `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`

이 문서의 중심은 검색을 더 넓히는 일도, 코드가 상태를 더 똑똑하게 정하는 일도 아니다. "이 값은 이 조건에 좌우된다 / 이 값에 필요한 조건 역할이 비었다"를 LLM/relation extractor가 역할 구조로 내고, `04` 코드 certification이 그 역할 구조를 읽어 state를 정하게 하는 것이다. 의미 판단의 자리를 코드도 검색도 아닌 여기에 둔다.

관련 판단:

- `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`
- `docs/implementation-notes/2026-06-29-certification-keyword-gate-mirror-trap/`
- `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`
- `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`
- `docs/engineering/llm-design.md`

## 왜 지금

위험 큰 자료(여행 예약)에서 가장 위험한 실패는 자료가 없어서가 아니라, 값은 맞는데 그 값을 조건부로 만드는 caveat가 같이 있는데도 "확정"으로 단정하는 것이다. P1-01이 그 자리다: `NonSmoke,LargeBed` 값과 "모든 특별 요청은 체크인 때 숙소 사정에 따라 결정된다"는 조건이 둘 다 자료에 있었는데, 최종 답은 값만 보고 "확정"이라 말했다. 못 찾은 게 아니라 찾았는데 안 쓴 것이다.

"이 조건이 이 값을 좌우하는가"는 의미 판단이다. 이 판단을 코드·검색·단일 LLM 호출에 떠맡기는 세 접근은 각각 다른 방식으로 무너진다.

1. 한 LLM 호출이 답과 상태를 함께 내면 자기 답을 자기가 인증해(self-certification) confident-wrong이 난다 — decision doc이 1급으로 귀속한 실패다(`docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`).
2. 코드가 질문/답변의 단어로 "이 질문이 조건 근거를 요구하나"를 판정하면, 같은 의미를 키워드 없이 물을 때(paraphrase) 게이트가 진입조차 못 해 confident-wrong이 그대로 통과한다 — 거울상 함정이다(`docs/implementation-notes/2026-06-29-certification-keyword-gate-mirror-trap/`).
3. 코드가 source unit `kind`와 page 근접으로 "조건이 값에 걸린다"를 추정하면, 한 page에 정책·비용·요청·주의가 다 모인 1~2장 문서에서 날짜처럼 무관한 깨끗한 값까지 강등된다 — 구조 프록시 함정이다(측정 근거: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`).

세 접근의 공통점은 의미 판단을 그 일에 맞지 않는 주체에게 떠넘긴 것이다. 단어 매칭도 page 근접도 "실제로 그 값을 좌우하는 조건"과 "그냥 근처에/같은 종류로 존재하는 조건"을 구분하지 못한다. 그 구분이 곧 보류해둔 entailment(근거가 주장을 받쳐주는지)이고, 그건 표현이 달라도 의미·맥락을 종합하는 일이라 LLM/relation extractor에 맞는 자리다(`docs/engineering/llm-design.md`의 책임 분리·relation-first·entailment). 코드는 그 결과인 역할 구조를 읽기만 한다.

P1-01은 coverage 문제가 아니다. 조건 후보는 이미 retrieval에 들어와 있었다 — `05`로는 풀리지 않는다. 따라서 `06`이 이 실패의 binding fix다.

## 사용자 장면

사용자가 예약 확인서에 대해 값과 조건이 함께 걸린 질문을 던진다.

예:

- "NonSmoke, LargeBed는 확정된 조건이야?"
- "금연이랑 큰 침대는 그냥 되는 거지?" (같은 의미를 키워드 없이 물은 paraphrase)
- "특별 요청한 거 그대로 적용돼?"

세 질문은 표현이 다르지만 같은 의미를 묻는다. 자료에는 값(`NonSmoke,LargeBed`)과 그 값을 조건부로 만드는 caveat("숙소 사정에 따라 결정")가 함께 있다. 이번 slice의 질문은 "더 많이 찾았는가"도 "코드가 단어를 잘 봤는가"도 아니라, **값과 조건의 관계를 의미로 읽어 표현이 바뀌어도 안정적으로 needs_review로 가는가**다.

## Product 흐름

```text
사용자 질문 + retrieval 후보 source unit (05)
-> 의미 층: relation extractor가 값↔조건 역할 구조 생성 (06)
-> code certification이 역할 구조를 읽어 final state 결정 (04)
-> final body rendering
-> 사용자에게 보이는 QA 결과
```

각 단계는 자기가 받은 것만 가지고 일하고, 다음 단계의 책임을 앞당겨 맡지 않는다.

| 단계 | 입력 | 출력 | 넘지 말 선 |
| --- | --- | --- | --- |
| 검색 (05) | 질문, source unit, metadata | role별 후보 source unit과 locator/kind/provenance, 후보가 값만/조건도 담는지 관찰 | "이 조건이 이 값을 좌우하는가"의 판정, final state, 답변 문장 |
| 의미 층 (06) | role별 후보와 그 원문 snippet/구조 metadata | evidence role(값 role, 그 값을 좌우하는 caveat role)과 caveat 관계, 필요한 조건 role이 비었음 | final state(상태 확정은 코드 몫), 새 값, 사용자-facing 문장 |
| code certification (04) | 정규화된 후보와 의미 층이 만든 역할 구조, grounding/value-grounding 구조 사실 | final evidence state, certification reason | `kind`·page 근접으로 조건을 추정, 질문/답변 단어를 읽은 의미 추측, 역할을 새로 발명 |
| final body | certified state와 certified facts | 사용자-facing 문장 | state 승격, 새 값 생성 |

이번 slice는 `retrieval 후보 -> 의미 층 -> code certification` 사이에 의미 층 계약을 세운다. 후보를 더 넓히는 일은 `05`, 상태를 정하는 일은 `04`가 소유하고, `06`은 그 사이의 역할·관계만 만든다.

## 무엇을 만드나 (계약)

relation extractor는 후보를 보고 evidence role과 caveat 관계를 만든다. 답이나 상태를 만들지 않는다.

만드는 것:

- **값 role** — 어떤 근거가 사용자가 물은 값/claim을 담는 근거인가.
- **caveat role** — 그 값을 조건부로 만드는 근거(예: "숙소 사정에 따라 결정")가 무엇인가.
- **caveat 관계** — "이 조건이 이 값을 좌우한다"는 관계. 단순히 한 page에 같이 있다거나 같은 kind라는 게 아니라, 의미상 그 조건이 그 값의 확정성을 좌우하는지다.
- **필요한 조건 role이 비었음** — 이 값을 확정으로 말하려면 어떤 조건 역할이 있어야 하는데 후보에 없거나 만들 수 없을 때, 그 비어 있음 자체를 신호로 낸다.

이 역할 구조가 `04` certification이 읽는 대상이다. relation extractor는 새 값을 만들지 않고(값은 후보에서 온다), 최종 상태도 정하지 않는다.

## 코드가 읽는 방식

`04` 코드 certification은 의미 층이 만든 역할 구조를 **읽기만** 한다. 의미를 분류하지 않는다.

- 값에 그 값을 좌우하는 caveat role이 붙어 있으면, 그 값은 단독으로 `supported`가 될 수 없다 — `needs_review`(또는 조건부)로 간다.
- 값에 필요한 조건 role이 비어 있다고 표시되면 `needs_review`로 간다.
- 값에 caveat role이 붙지 않았고 grounding/value-grounding이 통과하면, `04`의 mechanical check 범위 안에서 `supported`가 될 수 있다.

코드는 "이 문장이 조건인가", "이 질문이 조건을 요구하나"를 판정하지 않는다. 그 판정은 의미 층이 역할로 이미 내려 둔 것이고, 코드는 역할이 붙었는지 비었는지의 구조만 본다. 이렇게 두면 `04`가 단어(거울상 함정)도 `kind`·page 근접(구조 프록시 함정)도 쓰지 않으면서, 조건-좌우 판단을 다시 가질 수 있다.

## 경계

- **키워드 프록시 금지.** 의미 층의 역할 판정을 질문이나 답변의 키워드 매칭으로 만들지 않는다. 같은 의미를 키워드 없이 물어도 같은 역할 구조가 나와야 한다.
- **구조 프록시 금지.** source unit `kind`나 page 근접으로 "조건이 값에 걸린다"를 추정하지 않는다. `kind`는 후보를 모으는 보조 신호일 뿐, caveat 관계를 만드는 근거가 아니다. caveat 관계는 의미 판단이다.
- **안전 기본값.** caveat 관계 신호가 없거나 애매하면 `supported`가 아니라 `needs_review`로 간다. 위험 큰 자료에서는 모르면 확정하지 않는 쪽이 default다.
- **relation extractor 자체도 eval 대상.** 별도 검증을 둬도 그 검증기가 약하면 confident-wrong을 못 거른다. relation extractor의 판정은 후보가 어떤 순서·길이로 들어왔는지(position bias)와 자기가 낸 답인지(self-enhancement bias)에 흔들린다. 같은 입력을 순서만 바꿔 돌려 결과가 같을 때만 믿고, 추출 호출은 temperature 0으로 두거나 결정성을 확보한다(`docs/engineering/llm-design.md`의 출력 검증).
- **entailment 구현 방식은 미정.** "이 조건이 이 값을 좌우하는가"를 코드 entailment로 풀지 별도 모델로 풀지는 이 spec이 정하지 않는다. 방향(생성과 검증 분리, 의미 판단은 LLM/relation extractor)은 decision doc이 소유하고, `06`은 그 방향을 product slice로 운영하는 계약만 쓴다.

## 이 구조에서 막아야 하는 버그

1. 의미 층이 질문/답변 단어로 역할을 판정한다.
   - 막는 방법: 역할 판정 입력에서 질문/답변 keyword 게이트를 빼고, 후보의 원문 의미를 종합한다. paraphrase 회귀로 검증한다.
2. 코드가 의미 층 없이 `kind`·page 근접으로 조건을 추정한다.
   - 막는 방법: caveat 관계는 의미 층만 만들고, 코드는 역할 구조를 읽기만 한다.
3. caveat 관계 신호가 없을 때 위험한 쪽(`supported`)으로 떨어진다.
   - 막는 방법: 신호 부재·애매를 `needs_review`로 라우팅한다.
4. 의미 층 산출이 제품 응답 body로 새어 나간다.
   - 막는 방법: 역할 구조는 관찰 가능한 record로만 남기고, product response body에는 넣지 않는다.

통과 기준은 "규칙을 지켰다"가 아니라, 위 버그가 이 구조에서 날 수 있는지다.

## 구현 규칙

- product code는 eval dataset, expected cue, run artifact를 읽지 않는다.
- relation extractor가 만든 역할 구조는 LLM 후보·검색 후보를 보고 만들며, 질문셋 정답 문자열을 직접 주입하지 않는다.
- 의미 층은 새 값이나 final state를 만들지 않는다 — 역할과 관계만 만든다. 상태 확정은 `04` 코드 몫이다.
- 코드 certification은 의미 층이 만든 역할 구조를 읽되, `kind`·page 근접으로 조건을 추정하지 않고 질문/답변 단어를 읽지 않는다.
- caveat 관계 신호가 없거나 애매하면 `supported`가 아니라 `needs_review`로 간다.
- 의미 층 산출(역할·관계)은 관찰 가능한 record로 남길 수 있으나, product response body에는 observation/debug/eval field로 추가하지 않는다.
- 업체명이나 특정 질문 문구, 특정 값 문자열(`NonSmoke`·`LargeBed`)에 맞춘 예외처리로 역할을 만들지 않는다. lexical/kind는 `05`의 후보 recall 보조 신호일 뿐, `06`의 역할 판정 입력으로 쓰거나 역할·caveat 관계를 직접 만드는 근거로 쓰지 않는다 — `06`은 후보의 원문 의미를 종합해 역할을 만든다.

## Acceptance Criteria

1. 의미 층은 후보를 보고 evidence role(값 role, 그 값을 좌우하는 caveat role)과 caveat 관계, 필요한 조건 role의 비어 있음을 만든다. 새 값이나 final state는 만들지 않는다.
2. 코드 certification은 의미 층이 만든 역할 구조를 읽어 state를 정하고, 질문/답변 단어를 읽지 않는다.
3. 값에 그 값을 좌우하는 caveat role이 붙으면 그 값은 단독으로 `supported`가 되지 못한다(`needs_review` 또는 조건부).
4. 필요한 조건 role이 비어 있으면 final state는 `needs_review`로 간다.
5. caveat 관계 신호가 없거나 애매하면 `supported`가 아니라 `needs_review`로 간다.
6. binding paraphrase 회귀: "NonSmoke, LargeBed는 확정된 조건이야?"는 `needs_review`로 간다. 그리고 키워드 없는 동의 표현 "금연이랑 큰 침대는 그냥 되는 거지?"도 여전히 `needs_review`로 간다. 두 표현이 같은 역할 구조를 만들어야 한다.
7. 위 동작은 특정 문자열 하드코딩으로 만들어진 게 아니어서, 다른 자료에서 같은 값↔조건 구조가 나타나도 같은 판단이 유지된다.
8. 의미 층 산출(역할·관계)은 관찰 가능하되 product response body에는 추가되지 않는다.

## 확인 방법

1. relation extractor가 구현된 뒤, 측정 preflight를 거쳐 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 P1-01 특별 요청을 우선 확인하고, paraphrase 두 표현이 같은 역할 구조와 같은 `needs_review`로 가는지 본다.
3. 의미 층이 값 role과 그 값을 좌우하는 조건 role을 분리해 내고, caveat 관계를 만드는지 확인한다.
4. 코드 certification이 그 역할 구조를 읽어 state를 내리는지, 질문/답변 단어나 `kind`·page 근접에 기대지 않는지 확인한다.
5. 같은 입력을 후보 순서만 바꿔 돌렸을 때 역할 구조와 state가 같은지 확인한다(position/self-enhancement bias).
6. supported가 늘었는지만 보지 말고, 근거 부족한 supported(특히 조건이 함께 있는 값의 confident-wrong)가 줄었는지 확인한다.
7. product response body에 의미 층 산출이 새어 나가지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- role별 후보 coverage 일반화와 missing 원인 구분은 `05-subrequest-retrieval-coverage.md`에서 다룬다. `06`은 후보가 이미 들어온 P1-01류 케이스의 의미 판단에 집중한다.
- 모든 질문에 대한 일반 entailment 전면 스코어링은 이번 slice의 목표가 아니다 — 값↔조건 caveat 관계를 먼저 세우고, 일반화는 후속으로 둔다.
- 코드가 `kind`·page 근접으로 조건을 추정하는 구조 프록시는 `06`이 막는 대상이지 도입하는 것이 아니다(`docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`).
- entailment를 코드로 할지 별도 모델로 할지의 확정은 decision doc 존중하에 미정으로 둔다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 답변 문장 품질 개선만으로 이 slice의 성공을 선언하지 않는다.
