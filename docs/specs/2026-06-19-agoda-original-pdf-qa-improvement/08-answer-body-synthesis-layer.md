# Answer body 합성 층 분리

작성일: 2026-06-29 · 구현: 2026-06-30 (commit `84fbb18`)

상태: 구현됨. 사용자-facing 답변 문장(body)을 답변 생성 호출에서 떼어, **확정된 데이터를 읽고 맨 끝에 합성하는 전용 층**으로 옮겼다. `supported`·`needs_review` body는 합성으로 만들고, `missing`은 합성하지 않으며, 합성 실패·이상 출력 시 code template으로 폴백한다. 깨끗한 A/B(답변 모델만 변수, caveat 분리 호출 disabled·합성 모델 `gemma3:4b` 고정)로 측정했다.

기준 run (production·seed 20260624·repeat 3·caveat disabled·합성 모델 `gemma3:4b`):

- A(답변 모델 `gemma3:4b`): `eval/runs/question-dataset/26-20260630T-answer-gemma4b-body-gemma4b-caveat-disabled-A/`
- B(답변 모델 `qwen3:14b`): `eval/runs/question-dataset/27-20260630T-answer-qwen14b-body-gemma4b-caveat-disabled-B/`

질문별 수치·latency·P1-01 trace·구현 관찰은 `docs/implementation-notes/2026-06-30-answer-body-synthesis-layer/`에 보존한다(run artifact는 gitignore).

## 왜 지금

지금은 답변 LLM이 한 호출에서 body·value·evidence_state를 함께 내고, 코드 certification이 그 뒤에 state를 다시 정한다. 그래서 **body가 최종 payload와 어긋난다** — 이전 relation pass run(16·17)에서 관찰된 mismatch 유형(`docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`):

- label이 답과 안 맞음(날짜 아닌 질문에 label "체크인 날짜").
- 프롬프트 placeholder가 그대로 샘("short_snake_case_or_null"이 label로).
- body가 확정 결과와 따로 놂(body는 조건을 말하는데 state는 supported 등).

원인은 **body를 앞에서 미리 쓰고, 참(value/state/evidence)을 뒤에서 정하는 순서**다. 그래서 body 생성을 맨 끝으로 옮긴다 — `docs/engineering/llm-design.md`의 relation-first(claim·근거 먼저, 답변문은 그 관계를 푼 결과)를 답변 문장에 적용하는 것이다.

관련 판단:

- `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/04-answer-certification-boundary.md` (final body rendering 단계)
- `docs/engineering/llm-design.md` (relation-first, 생성/검증 분리)
- `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`

## 핵심: "무엇이 참인가"와 "어떻게 말하나"를 가른다

- **무엇이 참인가** — value·evidence·state는 앞에서 코드가 확정한다(지금 `04` 경로 그대로: 검색 → LLM 후보 → certification).
- **어떻게 말하나** — 맨 끝 LLM 호출이 그 확정 데이터를 읽고 사용자-facing 답변을 합성한다.

이 끝 호출은 **답변 생성에만 집중**하며 참을 바꾸지 못한다. needs_review를 "확정"으로 못 올리고, 없는 값을 못 지어낸다(`04` 가드레일 유지). 즉 상태는 코드가 들고, body는 그 상태를 문장으로 옮기기만 한다.

## Product 흐름

```text
사용자 질문 + retrieval 후보 source unit
-> LLM answer candidate (값/claim 후보, evidence ref)
-> code certification (value·evidence·state 확정)        ← 여기까지 04
-> body 합성 LLM 호출: 확정된 항목 전체를 읽어 답변 생성   ← 08 신설
-> 사용자에게 전달
```

이전 단계(검색·후보·certification)는 그대로 두고, `04`의 "final body rendering"을 **코드 template/LLM 초안 재사용**에서 **확정 데이터 기반 전용 LLM 합성**으로 바꾼다.

## body 합성 호출 계약

| 항목 | 내용 |
| --- | --- |
| 입력 | 질문 + certified items 목록(label, value, final state, evidence snippet) |
| 출력 | 사용자-facing 답변 문장 — 확정된 항목들을 종합한 하나의 coherent 답변 |
| 넘지 말 선 | state를 못 바꿈(needs_review→확정 금지), 새 값·새 근거 못 만듦, certified evidence 밖 사실 추가 금지 |
| 모델 | 답변(추출) 모델과 분리한 별도 호출(env `TRIPPROOF_OLLAMA_BODY_MODEL`, 기본 `gemma3:4b`). 어려운 판단은 앞에서 끝났으므로 작은 모델로 둔다 |
| 토글 | `TRIPPROOF_BODY_SYNTHESIS_ENABLED`로 끄면 합성 없이 code template body만 쓴다. "합성 vs template만"을 단일 변수로 재기 위한 측정 게이트다 |

상태별 어조는 `04`를 따른다: `supported`만 확정 어조, `needs_review`는 "확인 필요" 어조, `missing`은 없음. body 합성 LLM은 텍스트만 만들고 state 라벨을 쥐지 못한다 — state는 코드가 소유한 채 입력으로만 전달된다.

합성 실패·이상 출력(JSON 깨짐, id 불일치, prompt leak, `needs_review` body가 확정 표현을 씀)이면 합성 결과를 통째로 버리고 항목별 code template으로 폴백한다. 코드 안전망은 두 층이다: ① state가 합성 *전*에 잠겨 합성이 못 뒤집고, ② 폴백 template이 항상 깔려 있다. 단 `needs_review` 과잉확정 차단(`_looks_confirmed`)은 정확 문구 blocklist라 얇다 — 의미적 우회를 다 막지는 못하고, 진짜 방어는 ①과 합성 프롬프트다(상세: implementation-note).

## 이게 고치려는 것

- body가 final state·evidence와 **일치하도록 만든다**(위 mismatch 유형 해소가 목표).
- LLM 초안 잔재(틀린 label, placeholder 누수)가 최종 답변에 **새지 않게 한다** — body를 확정 데이터에서 새로 합성하므로.
- 항목들을 조각내지 않고 **하나의 종합 답변으로 묶는다**.

## Acceptance Criteria

1. body는 답변 LLM의 초안이 아니라, certification 뒤 별도 호출이 certified 데이터에서 생성한다.
2. body 합성 호출의 입력은 certified items(value/state/evidence)와 질문뿐이고, 이 호출이 final state를 바꾸지 못한다.
3. `needs_review`/`missing` 항목의 body가 "확정"처럼 말하지 않는다(`04` AC5 유지). paraphrase·표현이 달라도 state를 거스르지 않는다.
4. 틀린 label·프롬프트 placeholder 같은 초안 잔재가 최종 답변에 나타나지 않는다.
5. 여러 항목이 하나의 coherent 답변으로 종합된다.
6. body 합성은 추가 LLM 호출이므로 비용·latency를 관찰·기록하고, 개선이 측정될 때만 유지한다(`llm-design.md`).
7. product response body에는 observation/debug/eval field를 추가하지 않는다.

구현 상태: AC1·2·4·5·7은 코드로 충족하고 단위 테스트가 고정한다(합성이 `body`만 교체해 state/value/evidence 불변, missing은 template, 폴백, 초안 draft 미사용). AC3는 구조(잠긴 state)로 막되 표현 차단은 얇은 blocklist라 부분적이다. AC6의 latency는 측정했으나(아래) "개선이 측정될 때만 유지"는 미결 — 점수 이득이 작고 비용이 커서 모델·합성 유지 판단이 남았다.

## 측정 결과 (2026-06-30)

깨끗한 A/B(답변 모델만 변수). 둘 다 caveat 분리 호출 disabled, 합성 모델 `gemma3:4b` 고정.

- **rule pass**: A(답변 `gemma3:4b`) 1/8·1/8·1/8, B(답변 `qwen3:14b`) 2/8·2/8·2/8 — 평평하지 않고 일관된 +1.
- **완성도**: B가 준비물(신분증·결제카드), 위치, 객실/인원을 더 채웠고 P1-01을 `needs_review`로 옳게 보냈다. 다만 eval cue 채점이 부분문자열 게이트라 이 향상을 점수에 덜 반영한다(예: P1-01 B는 state는 맞췄으나 답에 "Remarks" 글자가 없어 fail). **pass 수를 제품 품질로 직접 환산하지 않는다.**
- **비용**: B(qwen 답변)가 문항당 ~47초로 A(gemma)의 ~6초 대비 ~8배 느렸다(8문항 셋 ~6.4분 vs ~50초). 관측은 명시 duration metric이 아니라 observation export 타임스탬프 간격 추론이다.
- **귀속**: 점수·완성도 차이는 **답변(추출) 모델 강약**에서 오지 body 합성층에서 오지 않는다. 합성층은 잠긴 사실을 문장으로 옮길 뿐이다. (수치·trace: implementation-note.)

## 확인 방법

1. 같은 원문 PDF·`questions.json`으로 실행해, certified state와 최종 답변 문장이 모순되지 않는지 본다(특히 `needs_review`가 "확정"으로 새지 않는지).
2. 틀린 label·placeholder 잔재가 사라졌는지 before/after로 본다.
3. 여러 항목 질문(객실/인원, 취소/노쇼)에서 답변이 하나로 종합되는지 본다.
4. 추가 호출의 비용·latency를 기록하고, body 품질 개선과 같은 저울에 올린다.
5. 실행 시 run 출처를 본문에 남긴다(README의 eval 출처 규칙).

## 열린 관찰: 값의 불확실성 표현이 안전망과 닿는 지점

깨끗한 A/B의 B(run 27, 답변 `qwen3:14b`, caveat 분리 호출 disabled)에서 P1-01("특별 요청은 확정인가")이 `needs_review`에 닿은 실효 경로가 드러났다: **답변 모델이 조건을 답변 payload 안에서 직접(inline) 냈고(`caveat_source: inline`), certify가 그 조건이 원문에 grounding됨을 보고 `limited_by_caveat`로 강등**했다. 별도 조건 검출기는 꺼져 있었다. 즉 이 케이스의 안전망은 "별도 검출기"가 아니라 **답변 모델 inline + 코드 grounding/certify** 조합에서 나왔다 — `07`의 방향 B(분리 호출 대신 inline)와 한 줄로 맞는 실데이터다. (같은 질문에서 약한 답변 모델 `gemma3:4b`(run 26)는 조건을 inline으로 못 내 `ungrounded → missing`으로 떨어졌다.)

이건 `08`의 분리 방향과 닿는 **가설**과 이어진다 — body 합성을 떼어내면, 답변 모델은 매끄러운 문장 대신 **값과 그 불확실성을 정직하게 표현**하는 데 집중할 수 있고, 안전망은 그 정직한 값에 대한 grounding 엄격성 + certify에서 나온다. 단 안전망 정밀도 자체의 결정은 `07`·`06` 영역이고, `08`은 표현/합성 분리만 다룬다. 또한 위 P1-01 성공은 강한 답변 모델(qwen)에 기댔고, 약한 모델에선 inline 자체가 비어 안전망이 안 선다 — 이 의존은 미해결로 `05`·`06`과 함께 본다.

## 이번 slice에서 섞지 않는 범위

- 상태 판정(value/state 확정)은 `04`가 소유한다 — 이 slice는 그 결과를 말로 옮기는 층만 바꾼다.
- relation 층 유지/모델 업그레이드 결정은 `07`이 다룬다.
- retrieval coverage는 `05`가 다룬다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 답변을 더 길고 친절하게 만드는 것 자체를 성공 기준으로 삼지 않는다 — 기준은 body가 확정 결과와 일치하는가다.
