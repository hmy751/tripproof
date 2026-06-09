# 구현 노트

이 폴더는 구현 중 드러난 오해, drift, 경계 관찰을 나중에 다시 볼 수 있게 남기는 자리다. 핵심은 대화 원문이나 진행 상황을 보존하는 것이 아니라, 비슷한 구현에서 다시 헷갈릴 수 있는 경계를 짧은 calibration sample로 남기는 것이다.

`docs/implementation-notes/`는 결정 기록이나 작업 재진입 로그가 아니다. 어떤 구조를 채택/기각/보류했다면 `docs/decisions/`에 두고, 다음 세션이 바로 이어받아야 할 얇은 진행 기록은 `docs/work-log.md`에 둔다. 제품 동작 기준과 AC는 `docs/specs/`가 소유한다.

## 원칙

구현 노트는 "이번에 무엇을 했나"가 아니라 "구현 중 어떤 판단 경계가 흐려졌고, 다음에는 무엇을 보고 멈춰야 하나"를 남긴다.

좋은 구현 노트는 특정 사건을 그대로 재현하지 않아도 다음 AI나 작업자가 비슷한 drift를 알아차리게 한다. 나쁜 구현 노트는 대화 분위기, 진행 목록, TODO, 개인 맥락을 남겨 다음 작업의 숨은 지시처럼 읽히게 한다.

## 남기는 것

- spec을 구현하다가 parent/인접 spec 계약을 잃은 사례.
- hard-coded value, fixture, stub, deterministic adapter가 product causality를 대신하려는 drift.
- LLM/RAG/evidence/state 같은 제품 경계를 구현 중 잘못 좁힌 사례.
- AI나 subagent가 반복해서 오해하기 쉬운 작업 경계.
- 이후 비슷한 구현에서 다시 확인할 짧은 guardrail.

## 남기지 않는 것

- 단순 진행 상황이나 완료 목록.
- 이미 decision note로 남길 구조적 선택.
- 현재 작업 queue나 TODO.
- 대화 원문, 개인 로컬 맥락, 내부 도구 운영 로그.
- 실제 product behavior나 코드 계약 없이 추정만 남긴 관찰.

## 좋음 / 나쁨

좋음:

- `03-evidence-backed-facts.md` 구현 중 하위 spec만 보고 02 source unit과 04 chat contract를 잃을 수 있음을 남긴다. 이유: 다음 구현에서 입력/출력 계약을 다시 확인하게 한다.
- "LLM provider 품질은 미룰 수 있지만, evidence quote 계약 자체를 hard-coded answer로 대체하면 안 된다"처럼 product causality 경계를 남긴다. 이유: 기술 충실도 축소와 제품 인과 제거를 구분하게 한다.
- "retrieval candidate는 accepted evidence가 아니다"처럼 상태 승격 경계를 남긴다. 이유: 비슷한 RAG 구현에서 같은 오해를 막는다.

나쁨:

- "오늘 03을 구현했고 여러 파일을 고쳤다"처럼 진행 상황을 남긴다. 이유: work-log나 commit에 가까워 구현 노트의 판단 기준이 되지 않는다.
- "AI가 이런 식으로 오해했다" 같은 대화 평가만 남긴다. 이유: 다음 구현자가 무엇을 확인해야 하는지 알 수 없다.
- "다음에는 04를 구현하자"처럼 작업 queue를 남긴다. 이유: 과거 노트가 현재 명령처럼 읽힐 수 있다.

## 작성 원칙

- 문서는 독립적으로 읽히는 중립 표현으로 쓴다.
- 원문 대화보다 구현 중 관찰된 문제와 다음에 볼 경계를 남긴다.
- 한 노트는 한 drift나 한 경계 관찰에 집중한다.
- 현재 실행 기준이 아니라 calibration sample로 읽히게 둔다.

## 판단 질문

- 이 기록은 다음 구현에서 같은 경계 오해를 발견하게 하는가?
- 이 내용이 결정이면 `docs/decisions/`, 재진입이면 `docs/work-log.md`, 제품 기준이면 `docs/specs/`가 더 맞지 않은가?
- 대화 원문 없이도 독립적으로 읽히는가?
- 이 노트가 다음 작업 queue나 승인 gate처럼 읽힐 위험은 없는가?
- 실제 코드, spec, product behavior에서 확인된 경계인가?

## 냄새 신호

- 날짜별 일지처럼 완료 목록이 중심이다.
- "해야 한다"가 많지만 어떤 drift를 막는지 드러나지 않는다.
- 개인 대화 표현이나 내부 도구 운영 흔적이 핵심 근거처럼 남아 있다.
- 한 노트에 여러 독립 drift가 섞여 있다.
- 코드나 spec에서 확인된 사실보다 추정과 감상이 앞선다.

권장 파일명:

```text
YYYY-MM-DD-짧은-주제.md
```

권장 형식:

```md
# YYYY-MM-DD - 제목

## 왜 남기나

## 관찰

## 다시 볼 경계

## 어디에는 남기지 않았나
```
