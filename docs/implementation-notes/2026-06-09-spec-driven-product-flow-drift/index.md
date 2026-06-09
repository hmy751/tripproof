# 2026-06-09 - Spec-driven slice와 제품 흐름 drift

## 폴더 구성

- `index.md`: 다음 구현에서 먼저 볼 관찰과 경계.
- `raw.md`: 이 관찰이 생긴 대화와 검토의 배경 재료.

`raw.md`는 현재 실행 기준이나 작업 대기열이 아니다. 현재 작업에 적용할 때는 이 `index.md`와 현재 코드 상태를 먼저 본다.

## 왜 남기나

숙소 체크인 04 구현 준비 중 `spec-driven` skill이 발동된 흐름과 발동되지 않은 흐름을 비교했다. 발동된 흐름에서는 `작게`, `얇게`, `slice`, `AC 1-3개` 같은 scope control 언어가 먼저 작동하며, `client가 facts[]를 렌더링`하는 방향이 더 작은 구현처럼 제안됐다.

이 방향은 04의 핵심인 `FactCandidate[] -> ChatAnswer -> 채팅 UI` 변환을 약하게 만들 수 있다. raw output을 화면에 붙이는 것은 제품 흐름을 통과한 답변과 다르다. 이 drift는 이후 RAG, evidence, state, card 승격 같은 구현에서도 반복될 수 있어 별도 구현 노트로 남긴다.

## 관찰

`spec-driven`의 light loop 자체는 여전히 유효하다. 작은 작업을 바로 진행하고, 큰 작업을 사용자 장면과 AC로 좁히며, 문서가 실행을 잡아먹지 않게 하는 장점이 있다.

문제는 제품 흐름을 먼저 고정하지 않은 상태에서 scope를 줄일 때 생긴다. AI는 `얇게`를 vertical slice가 아니라 가장 빨리 보이는 결과로 해석할 수 있다. 이때 `API 응답 그대로 렌더링`, `fixture 값 표시`, `debug output 노출`, `UI-only demo`가 제품 확인처럼 보이는 위험이 생긴다.

04 사례에서 제품 흐름은 다음에 가깝다.

```text
사용자 질문
-> ready materials
-> retrieval / fact candidates
-> supported/missing 상태를 반영한 ChatAnswer
-> 채팅 답변과 인라인 근거
```

따라서 `facts[]`를 raw list처럼 보여주는 것은 디버그나 임시 표시일 수는 있지만, 04 제품 확인 자체는 아니다. supported fact가 답변 주장과 연결되고, missing fact는 값을 만들지 않는 방식으로 표현되어야 한다.

## 다시 볼 경계

비슷한 구현에서 scope를 줄이기 전에 먼저 물어본다.

- 입력은 무엇인가?
- 이번 단계에서 어떤 변환을 해야 하는가?
- 사용자가 읽는 출력은 무엇인가?
- 넘지 말 선은 무엇인가?

좋은 좁힘은 필드 수, provider 품질, ingestion 충실도, UI polish를 줄이는 것이다. 나쁜 좁힘은 `근거/후보 -> 답변/상태 -> 화면`의 흐름 자체를 자르고 raw output을 완료처럼 보이게 하는 것이다.

좋은 좁힘과 나쁜 좁힘의 기준은 상황마다 달라질 수 있다. 제품 흐름을 어디서 잘라도 되는지 애매하면 AI가 임의로 다음 slice나 stub으로 넘기지 말고 사용자에게 확인한다.

## 어디에는 남기지 않았나

`docs/decisions/`에는 남기지 않았다. 이번 기록은 구조 채택/기각 결정이 아니라, 구현 중 반복해서 다시 볼 drift 관찰이다.

`docs/specs/`에는 남기지 않았다. 이 문서는 04의 제품 기준이나 AC를 새로 정하는 것이 아니라, spec-driven 운용 중 생긴 오해 가능성을 보존한다.

`docs/work-log.md`에는 남기지 않았다. 다음 작업 재진입 상태가 아니라, 비슷한 구현에서 다시 볼 calibration sample이다.
