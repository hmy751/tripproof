# Measurement reproducibility preflight

작성일: 2026-06-24

상태: implemented preflight. `02` source unit 구조화 이후, `04` product safety vertical에 들어가기 전에 before/after를 단일 run 인상으로 판단하지 않기 위한 측정 전제다.

이 문서는 product behavior 개선 slice가 아니다. 답변 품질을 올리는 것이 아니라, 이후 개선이 실제 동작 변화인지 LLM/runtime noise인지 구분할 수 있게 하는 최소 실행 조건을 다룬다.

## 사용자 장면

작업자는 같은 원문 PDF와 같은 질문셋으로 변경 전후를 비교한다. 이때 한 번 실행한 `run.json`만 보고 "좋아졌다" 또는 "나빠졌다"고 결론 내리면 안 된다.

특히 LLM answer composer가 포함된 실행은 temperature를 낮춰도 출력이 흔들릴 수 있다. 따라서 실행 조건과 코드 버전을 남기고, 필요할 때 같은 조건을 반복 실행해 현재 noise floor를 읽을 수 있어야 한다.

## Product 흐름

```text
원문 PDF + 질문셋
-> production-like product API 실행
-> run artifact 생성
-> commit/runtime/repeat/seed 조건 기록
-> 이후 product 개선 before/after 해석
```

이번 slice는 product 응답 body를 바꾸지 않는다. run artifact와 report가 실행 조건을 충분히 드러내는지를 다룬다.

## 개선 기준

측정 preflight는 아래를 가능하게 해야 한다.

- 어떤 코드 버전에서 실행했는지 알 수 있다.
- 어떤 runtime mode, answer composer, embedding provider, retrieval backend였는지 알 수 있다.
- deterministic smoke와 production-like original PDF run을 구분한다.
- 같은 조건을 N회 반복 실행해 질문별 흔들림을 관찰할 수 있다.
- seed나 유사한 provider 옵션을 쓴 경우 run artifact에서 확인할 수 있다.
- 단일 run의 rule pass를 release gate나 개선 proof로 과장하지 않는다.

## 구현 규칙

- product code가 eval artifact를 읽게 만들지 않는다.
- repeat 실행은 같은 product entry point를 여러 번 호출하는 관찰 장치로 둔다.
- seed 옵션은 provider가 지원하는 범위에서 additive하게 다룬다. seed가 없거나 provider가 무시하는 경우도 run artifact에 드러나야 한다.
- commit hash와 runtime snapshot은 실행 해석을 위한 메타데이터다. product response body에는 추가하지 않는다.
- `must_not_claim` 문자열 매칭이나 `state_matched` 같은 기존 rule check의 한계를 이 slice에서 semantic judge로 확장하지 않는다. 필요한 한계는 report와 spec에 명확히 남긴다.

## Acceptance Criteria

1. original PDF run artifact에서 commit hash 또는 이에 준하는 코드 버전 식별자를 확인할 수 있다.
2. run artifact에서 runtime mode, answer model, embedding provider/model, retrieval backend, retrieval top-k를 확인할 수 있다.
3. 같은 조건으로 같은 질문셋을 반복 실행할 수 있고, 반복 횟수가 run artifact나 run 묶음에서 확인된다.
4. seed를 지정한 실행과 지정하지 않은 실행이 구분된다.
5. report나 run 해석에서 단일 run의 rule pass를 제품 개선 proof로 단정하지 않는다.

## 확인 방법

1. 같은 원문 PDF와 같은 `questions.json`으로 preflight 전후의 run artifact 구조를 비교한다.
2. commit/runtime/repeat/seed 조건이 `run.json` 또는 run 묶음에서 확인되는지 본다.
3. 같은 조건의 반복 실행에서 P0-06, P1-01처럼 상태가 흔들릴 수 있는 질문을 우선 확인한다.
4. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 구현/측정 결과

구현 결과:

- `eval/run_question_dataset.py`가 단일 run artifact에 `code_version`, `run_config`, `repeat` 정보를 기록한다. dirty worktree에서는 raw diff 대신 tracked diff hash만 남긴다.
- `--repeat N` 실행은 각 반복을 독립 run folder로 남기고, 상위 `repeat.json`에서 run 묶음을 확인하게 한다.
- `--answer-seed`와 `TRIPPROOF_OLLAMA_ANSWER_SEED`를 통해 Ollama answer composer seed를 지정할 수 있고, 지정 여부는 run artifact runtime에 기록된다.
- product response body에는 request/correlation/debug/eval field를 추가하지 않았다.

preflight 확인 run:

- Repeat bundle: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/12-20260624T122630Z-measurement-preflight-repeat-seeded/repeat.json`
- 조건: original PDF, production runtime, `gemma3:4b`, temperature `0.0`, seed `20260624`, repeat `3`
- 결과: 세 반복 모두 rule pass는 `1/8`이었다. 다만 seed를 지정했어도 P0-06/P0-07은 반복별 상태가 흔들렸고, P1-01도 value-only `supported`와 `missing` 사이에서 달라졌다. 따라서 seed는 실행 조건 기록을 위한 옵션이지 결정성 보장으로 해석하지 않는다.

이 결과는 답변 품질 개선 proof가 아니다. `04` 이후 before/after에서는 같은 run 묶음 구조로 answer/evidence path 변화를 비교한다.

## 이번 slice에서 섞지 않는 범위

- answer certification boundary, retrieval coverage, answer assembly 개선을 넣지 않는다.
- semantic judge나 새로운 점수 threshold를 도입하지 않는다.
- release gate를 확정하지 않는다.
- 원본 PDF bytes나 raw provider payload를 `run.json` 또는 shared docs에 그대로 보존하지 않는다.
