# Raw Notes - certification 게이트 키워드 거울상 함정

이 파일은 `index.md` 관찰의 배경 재료다. 현재 실행 기준이나 작업 대기열이 아니다. 구현 시도 자체는 검증용이라 채택하지 않았고, 여기엔 다음에 같은 함정을 알아볼 만큼의 근거만 남긴다.

## 왜 raw가 필요한가

`index.md`의 경계("코드 게이트가 의미를 단어로 분류하면 무너진다")는 추상적으로만 두면 다시 같은 구현이 나온다. 정말 그렇게 무너지는지 재확인할 수 있게, 게이트의 lexical 형태와 실제 repro 입력/결과를 발췌로 남긴다.

## 무엇을 시험했나

한 구현 시도에서, `docs/engineering`의 판단 기준이 설계 진술에 실제로 반영되는지와, 반영된 원칙이 구현 코드까지 강제되는지를 함께 봤다.

- 실제 task(answer self-certification 슬라이스 구현)를 주되, `docs/engineering`·`llm-design`을 사전 컨텍스트로 직접 제공하지 않고, 구현 주체가 스스로 그 기준을 끌어오는지까지 관찰 범위에 뒀다.
- 과제 정의(해당 spec 슬라이스 + 자기인증 결정)만 주고, 어떤 기준이 설계에 반영돼 어떻게 운영되는지 봤다.

## 판단 기준은 설계에 반영됨 (성공 기록)

구현 주체가 코드 전에 진술한 설계 기준:

> LLM 출력은 final answer가 아니라 후보로 받고, 코드가 grounded evidence와 source unit metadata를 보고 최종 상태를 다시 정한다. 기준은 답변 문구가 아니라 "후보가 가리킨 source unit/snippet이 실제로 있고, 그 source unit kind/metadata 조합이 질문 요구를 뒷받침할 수 있는가"다.

이 진술은 `llm-design`의 책임 분리·생성검증 분리 원칙과 정확히 일치한다. 즉 판단 기준이 설계 진술에 반영됐고 headline 원칙은 흡수됐다. 구조도 그 진술대로 섰다(candidate ↔ final 분리, kind/metadata를 프롬프트 입력까지 보존, 관측 record에 candidate→final 전이 기록, 응답 body엔 debug/certification 필드 누수 없음).

## 그러나 구현이 샌 자리 (lexical 게이트)

설계 진술의 "질문 요구를 뒷받침하는가"에서, **"질문 요구"를 코드가 키워드로 분류**했다. 최종 state 경로를 가른 판정들이 모두 질문 문자열의 substring 매칭이었다.

- 확정성 질문 여부 = 질문에 `확정·보장·조건·confirmed·guaranteed·definite…` 포함 여부.
- 조건 문맥 요구 여부 = 질문에 `취소·노쇼·환불·수수료·비용·요금·세금·cancel·refund·fee·tax…` 포함 여부.
- 요구되는 evidence `kind` = 위 질문 키워드로 결정(예: 비용류 → fee/policy, 취소류 → policy).
- 시간 질문 강등 게이트 = 질문에 시간 단어가 있을 때만 답 모양을 검사하고 나머지는 통과(이전부터 약점으로 지목돼 있던 형태가 그대로 이어짐).

또한 게이트가 분기에 쓰는 source unit `kind`(예: `request_note`)도 원문 텍스트의 substring 키워드 분류기 산출이라, 게이트는 "질문 키워드 매칭 위에 자료 키워드 매칭"이 겹친 이중 lexical 구조였다.

## repro (확인된 사실)

같은 자료(값 unit "NonSmoke,LargeBed" + 조건 caveat unit)와 같은 후보 상태에서, 질문 표현만 바꿔 게이트를 통과시켜 본 결과:

- "NonSmoke, LargeBed는 확정된 조건이야?" (키워드 `확정·조건` 있음) → `needs_review`, body의 "확정된 조건입니다" 제거, 값 보존. (정상)
- "금연이랑 큰 침대는 그냥 되는 거지?" (같은 의미, 키워드 없음) → `supported`, body "확정된 조건입니다". (confident-wrong 부활)
- 키워드 없는 영어 caveat("subject to availability and not guaranteed")만 함께 있는 경우 → 그 caveat가 `kind=general`로 분류돼 게이트가 못 보고 → `supported`.
- 조건 caveat unit이 그 run의 retrieval에 안 들어온 경우 → 게이트 진입 실패 → `supported`.

즉 "확정" confident-wrong을 막으려던 게이트가, 질문을 자연스럽게 다르게 묻거나 자료 표현이 키워드를 벗어나면 같은 오답을 다시 통과시켰다.

## 확인된 사실과 해석

- 판단 기준이 설계 진술에 반영된 것은 성공이고, 그 원칙이 구현 코드까지 강제된 것은 실패다. 둘은 다른 일이다.
- 실패는 "entailment 검증이 없어서"가 1차 원인이 아니다(entailment 구현은 결정이 명시적으로 roadmap으로 보류했다). 1차 문제는 **그 빈자리를 구조 기준(값-only source unit은 조건/caveat kind 근거 없이는 `supported` 불가)이 아니라 질문 키워드로 메운 것**이다.
- 일반 교훈: 코드가 최종 상태를 쥐는 건 맞되, 그 계약의 판정 기준이 단어(질문이든 답변이든)면 같은 함정이다. 기준은 source unit kind/evidence set 구성이라는 구조여야 하고, 의미 판단은 LLM/relation extractor가 한다.

## 재진입 메모

- 구현 코드 자체는 검증용이라 버렸다(채택 안 함). 이 노트와 결정 후속(2026-06-25)·`llm-design` 일반 원칙이 남는 산출물이다.
- 다음에 certification 슬라이스를 실제로 구현할 때, 게이트 판정을 질문/답변 단어가 아니라 kind+evidence set 구성으로 세우고, 구조 신호 부재 시 default를 `needs_review`로 둔다.
