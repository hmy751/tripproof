# Relation 층 vs 모델 업그레이드 A/B

작성일: 2026-06-29

상태: draft sub-spec, 아직 미구현·eval 없음. `06` relation pass가 gemma3:4b에서 과잉강등으로 막힌 뒤(`docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`), 다음 수를 A/B 측정으로 결정하기 위한 spec이다. 결과를 미리 정하지 않고 비교 방법과 결정 기준만 둔다.

## 왜 지금

`06`에서 본 막힌 지점은 프롬프트·순서 트릭이 아니라 **gemma3:4b가 "이 조건이 이 답을 좌우하나"를 정밀히 못 가르는 모델 정밀도 천장**이었다. per-unit·순서불변(`118a916`)으로도 과잉강등을 못 잡아 되돌렸다(`8040665`). 그래서 다음은 모델 쪽 레버다 — 다만 두 갈래가 있고, 어느 쪽이 나은지는 측정으로만 안다.

핵심 질문: **좋은 모델이 생기면 relation 분리 층이 그 복잡도값을 하는가, 아니면 강한 모델 단독이면 충분한가.** (`docs/engineering/llm-design.md`: "복잡도는 측정으로 개선이 보일 때만 더한다"를 이 결정에 적용.)

관련 판단:

- `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/06-evidence-relation-extraction.md`
- `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`
- `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`
- `docs/engineering/llm-design.md`

## 두 갈래 (A/B)

같은 원문 PDF·같은 `questions.json`·같은 seed로 각각 돌려 비교한다.

- **A — relation 층 유지 + 더 강한 모델**: 분리 호출(caveat 검출)을 그대로 두되, 검출만 gemma3:4b보다 적절한/강한 모델로 돌린다. "분리 구조 + 좋은 검출기."
- **B — relation 층 제거 + 모델 업그레이드 단독**: 분리 호출을 빼고, 답변 모델 자체를 올려 분리 층 없이 처리한다. "강한 모델 단독."

`A`는 현재 baseline(분리 호출, `574dee4`)의 검출 모델을 바꾸는 것이고, `B`는 mechanical-only(분리 없음)에 강한 답변 모델을 얹는 것이다.

## 비교·결정 기준

단일 run으로 결정하지 않는다(`03` 재현성). repeat run으로 noise를 걷어낸 뒤, 아래를 같은 저울에 올린다.

- **P1-01 안전망**: 값을 좌우하는 조건이 있을 때 표현·키워드와 무관하게 안정적으로 `needs_review`로 가는가(paraphrase-stable).
- **과잉강등**: 깨끗한 lookup(날짜·위치·객실)이 불필요하게 `needs_review`로 내려가지 않는가(`supported` 유지).
- **비용·latency**: `A`는 답변 외 추가 호출, `B`는 더 큰 모델 — 정확도뿐 아니라 비용·지연도 같이 본다.

결정 규칙: **`A`(relation 층)는 `B`(모델 단독)보다 정밀도가 동등 이상이면서 비용이 정당할 때만 유지**한다. 그렇지 않으면 `B`로 가고 relation 층을 접는다. 결정은 "relation 층 유지/제거"로 명시 기록한다(필요하면 `docs/decisions/`).

## Acceptance Criteria

1. `A`·`B` 각각을 같은 원문 PDF·`questions.json`·seed로 eval하고, 결과를 before/after로 비교할 수 있다.
2. P1-01이 어느 안에서 paraphrase-stable `needs_review`로 가는지 관찰된다.
3. 깨끗한 lookup의 과잉강등 여부를 두 안에서 비교할 수 있다.
4. 비용·latency가 정밀도와 함께 기록된다(`A`의 추가 호출 수, `B`의 모델 크기).
5. 단일 run으로 결정하지 않는다 — repeat로 noise를 분리한 뒤 판단한다.
6. 결정 결과(relation 층 유지/제거 + 채택 모델)가 명시 기록된다.

## 확인 방법

1. `A`·`B` 두 런타임 구성으로 같은 원문 PDF·`questions.json`·seed로 각각 실행한다.
2. P1-01과 깨끗한 lookup(날짜·위치·객실)을 두 안에서 나란히 본다.
3. repeat로 변동을 걷어낸 뒤, 정밀도·과잉강등·비용을 표로 비교한다.
4. 결정과 그 run 출처를 본문/decision에 남긴다(README의 eval 출처 규칙).

## 이번 slice에서 섞지 않는 범위

- 모델 파인튜닝이나 새 임베딩/리트리버 도입은 이 결정의 대상이 아니다.
- 답변 body 생성 방식 변경은 `08`이 다룬다.
- retrieval coverage는 `05`가 다룬다.
- eval 점수 threshold나 release gate를 확정하지 않는다.

## 남은 판단

- "더 강한/적절한 모델" 후보(더 큰 Ollama 모델 / 클라우드 모델)는 구현 시 선택한다. 이 spec은 후보를 고정하지 않고, A/B 비교 틀과 결정 기준만 둔다.
