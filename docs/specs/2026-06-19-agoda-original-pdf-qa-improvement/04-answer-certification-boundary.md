# Answer certification boundary

작성일: 2026-06-24
재작성일: 2026-06-29

상태: draft sub-spec. source unit 구조화(`02`)와 측정 preflight(`03`) 이후, LLM 답변 후보가 자기 답을 스스로 인증하지 못하게 막는 첫 product safety vertical이다.

이 문서의 중심은 질문 분해 자체가 아니다. 검색이 가져온 source unit과 LLM이 만든 후보를 final answer로 바로 투영하지 않고, 그 사이에 code-owned certification boundary를 둔다. 최종 상태와 최종 문장은 이 boundary 뒤에서만 만들어진다.

관련 판단:

- `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`
- `docs/implementation-notes/2026-06-29-certification-keyword-gate-mirror-trap/`
- `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`
- `docs/engineering/llm-design.md`

## 구현 범위 재조정 (2026-06-29)

첫 구현을 같은 원문 PDF로 측정한 결과, 코드가 "조건이 이 값에 걸리는가"를 source unit `kind`와 같은-page 근접으로 추정한 두 강등 규칙(`conditional_source_kind`, `value_only_with_condition`)이 실제 1~2장 문서에서 과잉 강등을 일으켰다 — 날짜 등 조건과 무관한 깨끗한 값까지 전부 `needs_review`로 떨어졌다. 측정 run(2026-06-29, code `08f141e`): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/14-answer-certification-04-after-production/`. 근거와 repro: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`.

그래서 04가 **코드로 강제**하는 범위를 좁힌다.

- 강제(코드): candidate ↔ final 타입/단계 분리, 코드가 final state 소유, grounding(근거가 원문에 실재), value-grounding(답한 값이 근거에 실재 — "확정"을 값으로 들고 오면 여기서 걸림), final body는 certified state 뒤에서 생성, 응답 body에 debug/eval 누수 없음.
- 재귀속(의미 층): "값을 좌우하는 caveat가 있는가"의 판단. 이 의미 분류는 LLM/relation extractor가 역할로 내고(`docs/engineering/llm-design.md`), 그 후보 공급·coverage 관찰은 `05`가 받친다. 코드는 그 역할 구조를 **읽어** 상태를 정하되, `kind`·page 근접으로 조건을 **추정**하지 않는다.

아래 단계 계약과 AC의 조건 기반 부분(특히 value-only가 caveat와 함께일 때의 강등)은 이 의미 층이 역할 신호를 제공할 때 성립하는 목표다. 코드만으로 구조 신호 없이 그 판단을 흉내 내지 않는다.

이 재조정은 구현·검증됐다. `certify`에서 조건 추정 강등(`conditional_source_kind`, same-page `value_only_with_condition`)을 제거하고 grounding/value-grounding만 남긴 뒤, 같은 원문 PDF로 production run을 다시 돌려 과잉강등 해소를 확인했다 — 날짜·위치·객실이 `supported`로 복구됐고, 제거된 규칙 사유는 0건, 남은 `missing`은 LLM abstain(`candidate_missing`)뿐이었다. 검증 run(2026-06-29, mechanical-only fix는 이후 `989727c`로 커밋): `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/15-answer-certification-mechanical-only/`. 근거: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`.

## 사용자 장면

사용자가 예약 확인서에 대해 자연스러운 질문 하나를 던진다.

예:

- "취소하거나 노쇼하면 어떻게 돼?"
- "현장에서 추가로 내야 하는 비용이 있어?"
- "예약된 객실과 인원은 어떻게 돼?"
- "NonSmoke, LargeBed는 확정된 조건이야?"

위험한 실패는 자료가 없어서만 생기지 않는다. 특별 요청 질문에서는 `NonSmoke,LargeBed` 값과 "모든 특별 요청은 체크인 때 숙소 사정에 따라 결정"이라는 조건 문맥이 후보에 같이 있었는데도, 최종 답변은 값만 보고 "확정"이라고 말했다.

따라서 이번 slice의 질문은 "더 많이 찾았는가"가 아니라, **찾은 근거 이상으로 supported를 만들 수 있는 구조인가**다.

## Product 흐름

```text
사용자 질문 + retrieval 후보 source unit
-> LLM answer candidate
-> code certification
-> final answer item/state
-> final body rendering
-> 사용자에게 보이는 QA 결과
```

각 단계는 자기가 받은 것만 가지고 일한다.

| 단계 | 입력 | 출력 | 넘지 말 선 |
| --- | --- | --- | --- |
| 검색 | 질문, source unit, metadata | 후보 source unit과 locator/kind/provenance | final state나 답변 문장을 만들지 않는다 |
| LLM 후보 | 후보 source unit과 구조 metadata | 값/claim 후보, evidence ref, 불확실한 점, 필요한 근거 role | 사용자-facing body와 final `supported`/`needs_review`를 만들지 않는다 |
| code certification | 정규화된 후보와 evidence set 구조 | final evidence state, certification reason | 질문/답변 문구를 키워드로 읽어 의미를 추측하지 않는다 |
| final body | final state와 certified facts | 사용자-facing 문장 | state를 승격하거나 새 값을 만들지 않는다 |

이번 slice는 `LLM 후보 -> code certification -> final body` 경계를 product contract로 세운다. retrieval 후보를 더 넓히는 작업은 `05-subrequest-retrieval-coverage.md`에서 다룬다.

## 단계 계약

### 검색

검색은 source unit 후보를 찾고, 후보마다 원문 위치와 구조 단서를 보존한다.

필요한 단서:

- source unit id와 locator
- source unit `kind`/metadata
- 원문 snippet으로 되돌아갈 수 있는 provenance
- 후보가 값, 조건, 요청, 정책, 비용, 경고 같은 어떤 source unit 종류에서 왔는지

검색이 후보를 못 찾으면 그 자체가 coverage 문제다. 하지만 후보가 이미 있는데도 final answer가 값을 과신하면 retrieval 문제가 아니라 certification 문제로 본다.

### LLM answer candidate

LLM은 최종 답을 쓰는 사람이 아니라 후보를 만드는 사람이다.

LLM이 만들 수 있는 것:

- 후보 값 또는 claim
- claim을 뒷받침한다고 보는 evidence ref
- 조건, caveat, conflict, missing처럼 헷갈리는 점
- final answer에 필요하지만 현재 후보에서 부족한 evidence role

LLM이 만들면 안 되는 것:

- 사용자-facing 최종 문장
- final `evidence_state`
- "확정", "가능", "없음" 같은 제품 약속을 담은 최종 value

후보 schema에 임시 confidence나 rationale이 있을 수는 있지만, 그것은 product state가 아니다. 코드가 그대로 사용자-facing `ChatAnswerItem`으로 projection할 수 없어야 한다.

### Code certification

코드는 final state를 소유한다. 다만 의미를 단어로 분류하는 방식으로 소유하면 안 된다.

Certification이 볼 수 있는 것:

- candidate가 인용한 source unit id와 grounded snippet
- source unit `kind`/metadata
- evidence set 안의 role 구성(value, condition, caveat, conflict, missing role 등)
- evidence ref가 원문과 실제로 연결되는지

Certification이 받지 않거나 사용하지 않아야 하는 것:

- 원 질문의 free text
- LLM이 쓴 draft body
- 답변 문장 안의 "확정", "보장", "환불" 같은 단어
- question id, eval expected cue, run artifact

구조 신호가 없거나 애매하면 안전한 쪽으로 간다. 위험한 여행 예약 정보에서 기본값은 `supported`가 아니라 `needs_review` 또는 `missing`이어야 한다.

특히 value-only evidence는 그 값의 존재만 증명한다. 값이 사용자의 행동 판단까지 정당화한다는 뜻은 아니다. 요청 값에 그 값을 좌우하는 caveat role이 의미 층(`06`)에서 붙으면, final state는 "확정"이 아니라 조건부 또는 검토 필요로 내려가야 한다 — 이 강등의 trigger는 page 공존이 아니라 `06`이 만든 caveat role이다.

단, "caveat가 이 값에 걸린다"의 판정은 의미 판단이다(위 `구현 범위 재조정`). 코드는 이를 `kind`·page 근접으로 추정하지 않는다 — 실제 문서에서는 한 page에 정책·비용·요청·주의가 다 모여 있어 그 근접 추정이 무관한 값까지 강등시킨다. 이 판단은 LLM/relation extractor가 만든 역할 구성을 코드가 읽는 형태로만 성립한다. 코드가 단독으로 강제하는 것은 grounding과 value-grounding이고, 그것이 없으면 `supported`가 될 수 없다.

### Final body rendering

최종 문장은 certification 결과를 풀어 쓰는 마지막 단계다.

- `supported`는 certification이 확정한 사실만 말한다.
- `needs_review`는 확정처럼 말하지 않는다.
- `missing`은 없는 값을 추정하지 않는다.
- `conflict`가 생기면 한쪽을 임의로 고르지 않는다.

이 단계는 문장 품질을 다듬을 수 있지만, final state를 승격하거나 새 evidence를 만들 수 없다. 따라서 body가 state와 반대로 거짓말하는 길을 구조적으로 닫는다.

## 이 구조에서 막아야 하는 버그

1. LLM이 자기 답을 자기가 인증한다.
   - 막는 방법: LLM output에는 final state/body가 없다.
2. 코드가 질문이나 답변 단어로 의미를 분류한다.
   - 막는 방법: certification input에서 question/body free text를 빼고, source unit/evidence set 구조만 본다.
3. body가 state와 반대로 확정처럼 말한다.
   - 막는 방법: final body는 certified state 뒤에서만 생성한다.

통과 기준은 "규칙을 지켰다"가 아니라, 위 세 버그가 이 구조에서 날 수 있는지다.

## Decomposition의 위치

여러 값을 묻는 질문을 claim 후보 여러 개로 나누는 일은 여전히 필요하다. 다만 이번 04의 중심은 code가 질문 키워드를 보고 requirement를 만드는 일이 아니다.

허용되는 위치:

- LLM 후보 단계에서 source unit 후보를 바탕으로 claim/evidence relation을 여러 개로 나눈다.
- 별도 relation extractor가 structured claim과 evidence role을 만든다.
- code certification은 이미 정규화된 claim/evidence set을 받아 grounded 여부와 role 구성을 판정한다.

위험한 위치:

- code certification이 질문 free text를 읽고 "이 질문은 조건 질문"이라고 키워드로 분류한다.
- 답변 draft에 "확정"이 있으니 강등하거나, 질문에 "환불"이 있으니 정책 근거를 요구하는 식으로 텍스트 단어를 게이트로 삼는다.
- decomposition 결과가 없으면 위험한 쪽인 `supported`로 떨어진다.

Decomposition은 candidate를 더 잘 만들기 위한 수단이지, final state를 code keyword rule로 만들기 위한 우회로가 아니다.

## 구현 규칙

- product code는 eval dataset, expected cue, run artifact를 읽지 않는다.
- LLM answer candidate와 final `ChatAnswerItem`은 다른 타입/단계여야 한다.
- final `evidence_state`는 LLM 후보에서 그대로 복사하지 않는다.
- certification은 question/body free text keyword에 의존하지 않는다.
- source unit `kind`/metadata가 lexical annotation에서 왔더라도, 그 신호가 없거나 애매하면 safe fallback으로 간다.
- evidence snippet과 source reference가 없으면 `supported`가 될 수 없다.
- 값 evidence와 caveat evidence가 분리되어 있을 때 value-only evidence만으로 행동 판단을 확정하지 않는다.
- final body는 certified state와 facts에서 생성한다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

## Acceptance Criteria

> 구현 범위 재조정(위) 이후의 강제 주체: AC 1·2·5·7과 AC3의 value-grounding 부분("확정"을 값으로 들고 오면 차단)은 04 코드가 직접 강제한다. AC3의 조건 부분·AC4·AC6(값을 좌우하는 caveat가 함께일 때의 강등)은 의미 층(LLM/relation extractor + `05` coverage)이 역할 신호를 제공할 때 성립하는 목표이며, 코드가 `kind`·page 근접으로 흉내 내지 않는다.

1. LLM answer candidate schema에는 사용자-facing final body와 final `evidence_state`가 없다.
2. code certification은 question text나 draft body를 입력으로 받지 않고, source unit/evidence set 구조로 final state를 정한다.
3. P1-01 특별 요청 질문에서 `NonSmoke,LargeBed` value-only evidence만으로 `supported`가 되지 않는다.
4. P1-01에서 요청 값과 "숙소 사정에 따라 결정" 조건 문맥이 함께 후보에 있으면 final answer는 확정이 아니라 `needs_review` 계열로 표현된다.
5. final body는 certified state를 거슬러 "확정"처럼 말할 수 없다.
6. 취소/노쇼, 현장 추가 비용처럼 조건형 질문에서도 일부 값이나 비용명만으로 전체 정책을 `supported`로 만들지 않는다.
7. 같은 원문 PDF 질문셋을 실행했을 때 report에서 LLM candidate, certification result, final answer/evidence path를 before/after로 비교할 수 있다.

## 확인 방법

1. 측정 preflight 이후 같은 원문 PDF와 같은 `questions.json`으로 다시 실행한다.
2. report에서 P1-01 특별 요청을 우선 확인한다.
3. LLM candidate가 final state/body 없이 후보 값, evidence ref, uncertainty만 남기는지 본다.
4. certification 단계가 question/body text가 아니라 source unit kind, grounded refs, evidence role 구성으로 state를 낮추는지 확인한다.
5. final body가 certification state와 모순되지 않는지 확인한다.
6. supported가 늘었는지만 보지 말고, 근거 부족한 supported가 줄었는지 확인한다.
7. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 하위 요청별 retrieval coverage 전체를 이 slice에 넣지 않는다.
- lexical/kind/adjacent context 후보 보강을 이 slice의 성공 기준으로 삼지 않는다.
- UI 카드 승격이나 human review workflow 전체를 이 slice에 넣지 않는다.
- release gate나 점수 threshold를 확정하지 않는다.
- 원문 PDF 외 다른 업체별 fixture 일반화 평가를 이 slice의 필수 완료 기준으로 삼지 않는다.
- prompt 문장 품질만으로 개선 성공을 선언하지 않는다.
- code가 source unit `kind`나 page 근접으로 "조건이 값에 걸린다"를 추정하는 구조 프록시는 04 코드 범위 밖이다(의미 층으로 재귀속). 근거: `docs/implementation-notes/2026-06-29-certification-structural-proxy-overdowngrade/`.
