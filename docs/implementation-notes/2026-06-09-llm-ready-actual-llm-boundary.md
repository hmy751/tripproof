# 2026-06-09 - LLM-ready 구조와 실제 LLM 경로 구분

## 왜 남기나

숙소 체크인 03 구현 중 `RAG -> LLM/extractor -> validator -> fact candidate` 경계를 정리했지만, 실제 코드에서는 LLM provider를 호출하지 않고 `CheckinFactProposer` protocol과 `LocalCheckinFactProposer`로 후보 생성을 닫았다.

이 구조 자체는 테스트 double이나 fallback으로 쓸 수 있다. 문제는 이것을 "LLM을 반영했다"는 표현과 섞으면, 다음 구현자가 product causality를 잘못 이해할 수 있다는 점이다. `LLM-ready` 구조는 실제 LLM 판단 경로가 아니다.

## 관찰

현재 구현에서 확인되는 경계는 다음과 같다.

- `retrieve_context`는 source unit 후보를 고른다.
- `LocalCheckinFactProposer`는 후보 원문 안에서 정규식 기반 proposal을 만든다.
- `validate_fact_proposal`은 proposal의 snippet이 source unit 원문 일부인지 확인한 뒤에만 `supported`로 승격한다.
- `apps/server/llm/client.py`에는 structured output client protocol만 있고, 체크인 03 경로에서 실제 provider call은 없다.

따라서 현재 구현은 `RAG + local proposer + grounding validator`이다. `RAG + actual LLM judgement + grounding validator`라고 부르면 안 된다.

## 구현 경계 관찰

이 drift는 단순히 LLM adapter를 아직 붙이지 못한 문제가 아니라, hard-coded answer 우려를 구조 추상화 문제로만 해석하면서 실제 후보 생성 주체 확인이 늦어진 문제였다.

이 해석에서 세 가지가 섞였다.

- `provider 품질은 non-goal`이라는 spec 문장을 `provider call 자체도 생략 가능`에 가깝게 해석했다.
- `CheckinFactProposer` protocol을 만들면 나중에 LLM을 붙일 수 있다는 구조적 가능성을 현재 product path의 LLM 반영처럼 설명했다.
- `계약`, `candidate`, `validator`, `deterministic` 같은 개발자 용어로 구조를 설명하는 동안, 실제 응답 경로에서 proposal을 생성하는 주체가 무엇인지가 흐려졌다.

비슷한 경계 문제가 다시 나오면 먼저 코드 경로의 실제 행위자를 확인해야 한다. 확인할 것은 abstraction 이름이 아니라 값이 어디서 생기고 어떤 실행 경로가 기본값인지다.

## 다시 볼 경계

LLM provider 품질, prompt 고도화, 모델 평가는 뒤로 둘 수 있다. 그러나 어떤 주체가 fact proposal을 만들었는지는 미루거나 흐리면 안 된다.

비슷한 구현에서 다시 확인할 질문:

- 코드 경로가 실제 LLM client를 호출하는가, 아니면 protocol/interface만 있는가?
- fallback이나 test double이 기본 production path로 들어가 있다면 이름과 응답에서 그 사실이 드러나는가?
- "LLM이 판단한다"는 spec 문장을 만족했다고 말하려면, 실패/비활성화/테스트 모드가 아닌 경로에서 provider call을 검증하는 테스트가 있는가?
- validator가 evidence grounding을 보장하더라도, proposal 생성 주체를 LLM처럼 표현하고 있지는 않은가?

이 경계는 "정규식을 절대 쓰면 안 된다"가 아니다. 정규식은 validator, fallback, fixture smoke, deterministic baseline에 쓸 수 있다. 다만 정규식 proposal이 실제 LLM 판단을 대신했으면 그 구현은 LLM 통합 완료가 아니라 local proposer 구현이다.

## 어디에는 남기지 않았나

- `docs/decisions/`: provider를 선택하거나 구조를 채택/기각한 결정이 아니라, 구현 중 경계가 흐려진 관찰이다.
- `docs/work-log.md`: 진행 기록보다, 비슷한 구현에서 다시 볼 calibration sample에 가깝다.
- `docs/specs/`: 제품 기준은 이미 03 spec에 있다. 이 문서는 spec 자체가 아니라 구현 표현과 실제 코드 경로 사이의 drift를 다룬다.
