# Raw Notes - Spec-driven skill / README 축약과 복구 기준

이 파일은 `index.md` 관찰의 배경 재료다. 현재 실행 기준이나 작업 대기열이 아니다.

## 왜 raw가 필요한가

이번 기록은 단순한 문구 축약에서 나온 것이 아니었다. `spec-driven` skill은 TripProof에서 큰 작업, AI/LLM 경계, product-first/eval 경계, spec/decision/work-log 기록 위치를 판단하게 하는 repo-local runtime 장치다. 그만큼 이전 작업에서 의도적으로 보강한 문장이 많았고, 줄이는 과정에서 중요한 guardrail이 빠질 수 있었다.

초기 검토에서는 이 skill을 어떤 관점에서 점검해야 하는지가 쟁점이었다. prompt 작성, 실행 하네스, LLM workflow를 각각 분리해 보는 단일 관점만으로는 부족했고, skill이 쌓인 이유와 TripProof 기록의 맥락을 함께 보는 쪽으로 논의가 좁혀졌다.

## 대화·조사에서 드러난 문제 감각

처음 검토는 skill을 너무 일반적인 prompt / harness 관점에서 정리하려는 흐름이 있었다. 이 방향은 최근 implementation note와 work-log에서 의도적으로 남긴 제품 흐름 guardrail을 지울 수 있다는 문제가 드러났다. 특히 다음 경계가 중요했다.

- raw output을 product result처럼 보지 않는다.
- scope를 줄이더라도 `사용자 자료 -> 근거/후보 -> 답변/상태 -> 화면` 흐름을 자르지 않는다.
- fixture/seed 값 맞추기가 product proof가 되면 안 된다.
- LLM-ready 구조와 실제 LLM 판단 경로를 섞지 않는다.
- 애매하면 AI가 임의로 다음 slice나 stub으로 넘기지 말고 사용자에게 확인한다.

이후 관점별 검토는 decision, implementation notes, work-log, git history, 현재 skill / README diff를 직접 보게 하는 방식으로 다시 수행했다. 관점은 크게 셋이었다.

- LLM workflow 관점: LLM-ready, fallback, deterministic path가 실제 LLM 판단처럼 표현되는지 확인.
- principle / calibration 관점: skill 축약이 다음 판단 감각을 잃게 하지 않는지 확인.
- product / harness boundary 관점: product-first, eval observes product, raw/stub/fixture 경계가 남았는지 확인.

## 확인된 사실과 해석

관점별 검토의 공통 결론은 긴 skill 전체를 되돌리는 것이 아니라, runtime core와 calibration reference를 나누는 방향이었다.

보존해야 한다고 본 축:

- product가 먼저이고 eval은 product behavior를 관찰한다.
- product-first는 implementation-first가 아니다.
- AI/LLM output은 목표가 아니라 후보이며, human review와 evidence/card 경계를 흐리지 않는다.
- raw candidate, fixture value, retrieval/debug/API/LLM output은 사용자-facing answer/state로 변환되기 전까지 product result가 아니다.
- LLM-ready interface, fallback, deterministic path를 actual LLM 판단 경로처럼 표현하지 않는다.
- 기존 spec 구현 전에는 parent/인접 spec의 입력/출력 계약을 짧게 확인한다.
- spec/AC가 특정 fixture/seed 문장이나 값 맞추기로 좁아지면 drift로 본다.

README에 두는 편이 낫다고 본 축:

- 자세한 spec 읽기 순서.
- 용어와 calibration examples.
- 좋음/나쁨 예시.
- 완성본에 가까운 숙소 체크인 spec sample.

복원하지 않는 편이 낫다고 본 축:

- 긴 숙소 체크인 brief 예시를 skill runtime에 되돌리는 것.
- `FactCandidate[] -> ChatAnswer` 같은 04 전용 문구를 일반 skill 표준으로 올리는 것.
- work-map, execution-map, full SDD, 모든 작업 spec/eval/log화.
- 과거 raw note나 관점별 검토 내용을 현재 작업 queue처럼 되살리는 것.

## 반영된 변경

이번 개편에서 `SKILL.md`는 길이를 줄이되 다음 runtime guardrail을 남겼다.

- 실행 계약, 우선순위, 제품 흐름 경계, Light Brief, 기존 spec 구현 전 질문, 기록 위치, Runtime Smells로 재구성했다.
- product-first / eval observes product, product-first != implementation-first, AI/LLM output은 후보라는 문구를 skill에 남겼다.
- raw/debug/API/LLM output, LLM-ready vs actual LLM, deterministic/stub test double 경계를 skill에 남겼다.
- Runtime Smells에 fixture/seed 문장이나 값 맞추기로 좁아지는 drift를 추가했다.

`docs/specs/README.md`는 다음 방향으로 조정했다.

- "구현 전에"라는 선행 gate 느낌을 줄이고, 큰 작업에서 기준을 맞추는 loop로 표현했다.
- 읽기 순서를 필수 실행 순서가 아니라 읽는 렌즈라고 명시했다.
- Light Brief에 `제품 흐름(필요할 때만): 입력 -> 변환 -> 출력 / 넘지 말 선`을 추가했다.
- skill과 README/examples가 매번 읽는 gate가 아니라 calibration reference임을 명시했다.

내부 운영 주체처럼 읽힐 수 있는 표현은 공개 문서에서 독립적으로 읽히도록 중립 표현으로 정리했다.

## 복구 메모

이번 개편은 큰 정리다. 잘 작동하지 않으면 더 많은 보완문을 덧대기보다 먼저 직전 기준으로 되돌리는 선택지를 본다.

복구 기준:

```text
이번 spec-driven skill / README 축약이 실제 작업에서 제품 흐름 손실, fixture/seed 값 맞추기, raw output을 product result로 보는 drift, 또는 README/skill의 새로운 gate화를 만든다면, 이 변경을 계속 덧대기보다 작업 전 기준으로 되돌리는 선택지를 먼저 검토한다. 작업 전 기준은 현재 개편 직전 git HEAD인 6adc709의 `.claude/skills/spec-driven/SKILL.md`와 `docs/specs/README.md`다.
```

이 기준은 자동 rollback 명령이 아니라 다음 판단의 기준이다. 문제가 반복되면 `index.md`의 경계를 먼저 보고, 현재 상태에서 한두 줄 보강으로 해결할 수 있는지와 직전 기준 복구가 더 나은지를 비교한다.

## 재진입 메모

다음에 이 skill이나 README를 다시 손볼 때는 먼저 아래를 확인한다.

- 현재 변경이 skill을 가볍게 하는가, 아니면 guardrail을 제거하는가?
- README가 calibration reference로 남아 있는가, 아니면 hidden playbook이나 gate가 되는가?
- implementation note와 work-log의 관찰이 현재 작업 명령으로 승격되고 있지는 않은가?
- 문제가 생긴 상태에서 새 문구를 덧대는 것이 더 낫나, `6adc709` 기준으로 되돌리는 것이 더 낫나?
