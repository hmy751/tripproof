# 2026-06-09 - Spec-driven skill / README 축약과 복구 기준

## 폴더 구성

- `index.md`: 다음 작업에서 먼저 볼 관찰, 보존한 경계, 복구 기준.
- `raw.md`: 이번 축약이 필요해진 논의와 관점별 검토의 배경 재료.

`raw.md`는 현재 실행 기준이나 작업 대기열이 아니다. 현재 작업에 적용할 때는 이 `index.md`와 현재 skill / README 상태를 먼저 본다.

## 왜 남기나

`.claude/skills/spec-driven/SKILL.md`가 여러 차례 보강되며 제품 흐름, LLM 경계, fixture/stub 경계, 기록 위치, 예시가 한 파일에 많이 쌓였다. 이 상태는 의도된 guardrail을 보존한다는 장점이 있었지만, skill 자체가 긴 hidden playbook이나 절차 gate처럼 읽힐 위험도 커졌다.

이번 작업은 skill을 runtime core로 줄이고, 자세한 용어와 calibration examples는 `docs/specs/README.md`가 소유하도록 나누는 개편이었다. 동시에 최근 구현 중 일부러 남긴 제품 흐름 guardrail이 사라질 수 있다는 우려가 있어, decision / implementation note / work-log / git history를 다시 확인하며 보존할 축을 재검토했다.

## 관찰

좋은 축약은 세부 예시와 오래된 절차를 줄이되, 다음 작업에서 같은 판단 감각을 다시 만들 수 있는 runtime guardrail은 남긴다. 이번 개편에서 skill에는 다음 축을 남겼다.

- 현재 요청 범위와 수정 권한을 먼저 본다.
- product가 먼저이고 eval은 product behavior를 관찰한다.
- product-first는 implementation-first가 아니며, 사용자 자료가 후보/근거, 답변/상태, 화면으로 이어지는 인과를 먼저 본다.
- AI/LLM output은 목표가 아니라 후보이며, 사람의 채택/기각, evidence state, card 승격 경계를 흐리지 않는다.
- raw candidate, fixture value, retrieval/debug/API/LLM output은 사용자-facing answer/state로 변환되기 전까지 product result가 아니다.
- LLM-ready interface, fallback, deterministic path를 실제 LLM 판단 경로처럼 표현하지 않는다.
- 현재 spec/AC가 특정 fixture/seed 문장이나 값 맞추기로 좁아지면 drift로 본다.

자세한 읽기 순서, 용어, 좋음/나쁨 예시, 완성본에 가까운 calibration sample은 `docs/specs/README.md`에 둔다. README도 매번 읽는 gate가 아니라, scope 축소나 product path 판단이 흔들릴 때 감각을 보정하는 reference로 둔다.

## 복구 기준

이번 개편이 실제 작업에서 좋지 않게 작동하면, 더 많은 보완문을 덧대기 전에 우선 작업 전 기준으로 되돌리는 선택지를 검토한다.

복구 메시지:

```text
이번 spec-driven skill / README 축약이 실제 작업에서 제품 흐름 손실, fixture/seed 값 맞추기, raw output을 product result로 보는 drift, 또는 README/skill의 새로운 gate화를 만든다면, 이 변경을 계속 덧대기보다 작업 전 기준으로 되돌리는 선택지를 먼저 검토한다. 작업 전 기준은 현재 개편 직전 git HEAD인 6adc709의 `.claude/skills/spec-driven/SKILL.md`와 `docs/specs/README.md`다.
```

이 메시지는 복구를 자동 실행하라는 명령이 아니다. 다음 작업자가 현재 상태에서 문제가 반복된다고 판단할 때, "더 보강할지"보다 "직전 기준으로 되돌릴지"를 먼저 검토하라는 재진입 기준이다.

## 다시 볼 경계

비슷한 skill / README 정리에서 먼저 묻는다.

- 줄이는 대상이 예시와 절차인가, 제품 흐름 guardrail인가?
- runtime skill에 남아야 할 것은 즉시 판단을 바꾸는 냄새 신호인가?
- README로 넘긴 내용이 실제로 calibration reference로 남아 있는가?
- 특정 feature 예시가 다른 feature의 hidden playbook처럼 읽히지는 않는가?
- 새 문구가 과거 기록, 관점별 검토, raw note를 현재 작업 queue나 승인 gate로 되살리지는 않는가?
- 문제가 생겼을 때 보완문을 더 붙이는 것이 아니라 직전 기준 복구가 더 나은가?

## 어디에는 남기지 않았나

`docs/decisions/`에는 남기지 않았다. 이번 작업은 새로운 방법론을 채택한 decision이라기보다, 이미 남아 있던 light spec-driven / product-first / gate 방지 결정을 현재 skill과 README에 다시 배치한 구현 중 경계 관찰이다.

`docs/specs/`에는 새 spec으로 남기지 않았다. 제품 동작 기준이나 AC가 아니라, spec 운영 skill과 README의 유지보수 경계다.

`docs/work-log.md`에는 링크만 남긴다. 다음 세션 재진입에는 필요하지만, 자세한 배경과 복구 기준은 이 implementation note가 소유한다.
