# Answer body 합성 층 분리

작성일: 2026-06-29

상태: draft sub-spec, 아직 미구현·eval 없음. 사용자-facing 답변 문장(body)을 답변 생성 호출에서 떼어, **확정된 데이터를 읽고 맨 끝에 합성하는 전용 층**으로 옮기기 위한 spec이다.

## 왜 지금

지금은 답변 LLM이 한 호출에서 body·value·evidence_state를 함께 내고, 코드 certification이 그 뒤에 state를 다시 정한다. 그래서 **body가 최종 payload와 어긋난다** — eval에서 실제로 본 증상:

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

상태별 어조는 `04`를 따른다: `supported`만 확정 어조, `needs_review`는 "확인 필요" 어조, `missing`은 없음. body 합성 LLM은 텍스트만 만들고 state 라벨을 쥐지 못한다 — state는 코드가 소유한 채 입력으로만 전달된다.

## 이게 고치는 것

- body가 final state·evidence와 **일치**한다(앞의 mismatch 증상 해소).
- LLM 초안 잔재(틀린 label, placeholder 누수)가 최종 답변에 안 샌다 — body는 확정 데이터에서 새로 합성되니까.
- 항목들이 조각나지 않고 **하나의 종합 답변**으로 나온다.

## Acceptance Criteria

1. body는 답변 LLM의 초안이 아니라, certification 뒤 별도 호출이 certified 데이터에서 생성한다.
2. body 합성 호출의 입력은 certified items(value/state/evidence)와 질문뿐이고, 이 호출이 final state를 바꾸지 못한다.
3. `needs_review`/`missing` 항목의 body가 "확정"처럼 말하지 않는다(`04` AC5 유지). paraphrase·표현이 달라도 state를 거스르지 않는다.
4. 틀린 label·프롬프트 placeholder 같은 초안 잔재가 최종 답변에 나타나지 않는다.
5. 여러 항목이 하나의 coherent 답변으로 종합된다.
6. body 합성은 추가 LLM 호출이므로 비용·latency를 관찰·기록하고, 개선이 측정될 때만 유지한다(`llm-design.md`).
7. product response body에는 observation/debug/eval field를 추가하지 않는다.

## 확인 방법

1. 같은 원문 PDF·`questions.json`으로 실행해, certified state와 최종 답변 문장이 모순되지 않는지 본다(특히 `needs_review`가 "확정"으로 새지 않는지).
2. 틀린 label·placeholder 잔재가 사라졌는지 before/after로 본다.
3. 여러 항목 질문(객실/인원, 취소/노쇼)에서 답변이 하나로 종합되는지 본다.
4. 추가 호출의 비용·latency를 기록하고, body 품질 개선과 같은 저울에 올린다.
5. 실행 시 run 출처를 본문에 남긴다(README의 eval 출처 규칙).

## 이번 slice에서 섞지 않는 범위

- 상태 판정(value/state 확정)은 `04`가 소유한다 — 이 slice는 그 결과를 말로 옮기는 층만 바꾼다.
- relation 층 유지/모델 업그레이드 결정은 `07`이 다룬다.
- retrieval coverage는 `05`가 다룬다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
- 답변을 더 길고 친절하게 만드는 것 자체를 성공 기준으로 삼지 않는다 — 기준은 body가 확정 결과와 일치하는가다.
