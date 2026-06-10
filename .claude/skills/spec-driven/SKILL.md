---
name: spec-driven
description: TripProof repo 전용 light spec-driven 실행 판단 스킬. 현재 요청이 spec/AC/product contract를 만들거나, 읽거나, 기준으로 적용·수정하는 작업일 때 사용한다. 일반 구현 설명, 코드 탐색, 제품 흐름 설명은 spec 기준으로 판단하라는 요청이 아닌 한 발동하지 않는다.
---

# Spec-driven

이 skill은 TripProof에서 spec-driven을 repo gate가 아니라 현재 요청의 가벼운 실행 루프로 쓰게 한다. 목적은 사용자 장면, 제품 흐름, 이번 완료 기준을 짧게 맞춰 사람과 AI가 같은 통과 조건을 보게 하는 것이다.

자세한 spec 운영 기준, 용어, 읽는 순서, calibration examples는 `docs/specs/README.md`가 소유한다. 이 skill은 README를 반복하지 않고, agent가 지금 brief를 만들지, 바로 구현할지, 멈춰 확인할지 판단하는 runtime core만 다룬다. 이 skill이 켜졌다는 이유만으로 README를 매번 읽는 gate를 만들지 않는다. 다만 scope 축소, raw output, stub, AI 후보, product/eval 경계가 흔들리면 README는 짧게 참고하는 calibration reference다.

## 실행 계약

- 현재 사용자 요청의 범위가 먼저다.
- 이 skill은 spec/AC/product contract가 현재 요청의 판단 기준일 때만 켠다. 제품·코드 흐름을 설명하는 요청은 그 흐름을 spec 기준으로 평가하거나 바꾸라는 요청이 아닌 한 대상이 아니다.
- read-only/review 요청이면 판단만 보고하고 파일을 고치지 않는다.
- 구현 요청이면 작은/큰 작업을 판단한 뒤 진행한다.
- 이 skill은 새 spec 파일 생성, 문서 수정, stage/commit 권한을 자동으로 부여하지 않는다.
- 작은 작업은 과절차화하지 않는다. 오타, 문구, 좁은 UI 조정, 기존 AC 안의 bugfix, 단일 파일 refactor, 이미 선택된 feature의 테스트 보강은 바로 진행할 수 있다.
- 큰 작업은 light brief로 시작한다. 사용자 flow, AI 위임 범위, AC, 실패 유형, 제품 계약, evidence state, human review, card 승격, eval 관찰 대상이 바뀌면 큰 작업으로 의심한다.
- product가 먼저다. spec, brief, eval은 product behavior를 확인하는 보조 도구이며, product code가 eval fixture, runner, metric output에 의존하게 하지 않는다.
- product-first는 implementation-first가 아니다. 바로 보이는 코드 조각보다 사용자 자료가 후보/근거, 답변/상태, 화면으로 이어지는 인과를 먼저 본다.
- AI/LLM output은 목표가 아니라 후보다. 사람의 채택/기각, evidence state, card 승격 경계를 흐리지 않는다.

## 우선순위

1. 요청 범위와 수정 권한을 확인한다.
2. 작은 작업인지 큰 작업인지 가른다.
3. 작게 자르기 전에 줄이면 안 되는 제품 흐름을 본다.
4. 큰 feature라면 AC로 바로 뛰지 않고 구현면을 펼친 뒤 slice 후보를 본다.
5. 이번에 화면까지 이을 slice 하나와 관찰할 AC 1-3개를 고른다.
6. 구현 직전, 이 출력의 실제 행위자가 LLM인지 코드 규칙인지 한 줄로 보고(→ 제품 흐름 경계), 구현·수동 확인 또는 테스트 관찰·기록 위치를 선택한다.

이 순서는 승인 gate가 아니다. 이미 경로가 좁은 bugfix나 작은 spec이면 구현면 펼치기를 생략할 수 있고, 생략할 때는 왜 생략하는지 한 줄로 충분하다.

### Surface 이후 실행 순서

Implementation Surface를 펼친 뒤에는 상위 wrapper, provider, umbrella module, 하위 spec 구조부터 구현 대상으로 삼지 않는다. 먼저 product path 안에서 실제 fact/record를 생성하는 leaf producer를 고른다.

Adapter, exporter, provider abstraction은 leaf producer가 만든 record를 소비할 때만 만든다. 아직 소비할 product payload가 없다면 no-op wrapper나 provider client는 첫 slice가 아니다.

Leaf producer first는 helper/type/schema를 먼저 만들라는 뜻이 아니다. 해당 slice는 사용자 흐름의 endpoint 또는 domain boundary에 연결되어야 하며, 첫 구현 작업을 고를 때는 이 작업이 어떤 endpoint/domain에서 어떤 product fact를 생성하는지 한 문장으로 확인한다.

## 제품 흐름 경계

줄일 수 있는 것은 범위, 필드 수, provider 품질, ingestion 충실도, 화면 다듬기다. 줄이면 안 되는 것은 `사용자 자료 -> 근거/후보 -> 답변/상태 -> 화면`의 흐름이다.

- 자료가 바뀌면 답도 바뀌어야 한다.
- evidence quote가 없으면 `근거 있음`이 될 수 없어야 한다.
- raw candidate, fixture value, retrieval/debug/API/LLM output은 사용자-facing answer/state로 변환되기 전까지 product result가 아니다.
- 값/판정을 만드는 실제 행위자가 LLM 판단인지 코드 내부 규칙(키워드·패턴·고정 phrase)인지, 자료가 바뀌면 출력이 바뀌는지가 흐려지면 멈춰서 본다.
- deterministic baseline이나 stub은 같은 계약을 통과시키는 test double일 수 있지만, 제품 확인의 주인공이 되면 안 된다.
- 좋은 좁힘과 나쁜 좁힘이 애매하면 AI가 임의로 `다음 slice`나 stub으로 넘기지 말고 사용자에게 짧게 확인한다.

이 판단이 애매할 때만, 추상 규칙이 아니라 `docs/implementation-notes/`에서 같은 미끄러짐을 기록한 비슷한 사례를 찾아 calibration으로 참고한다(선행 필독 아님). 예: `docs/implementation-notes/2026-06-09-llm-ready-actual-llm-boundary.md`(LLM 자리에 코드 규칙이 들어갔는데 abstraction 이름이 그 사실을 가린 경우), `docs/implementation-notes/2026-06-09-spec-driven-product-flow-drift/`(scope 축소가 변환 단계를 건너뛰고 raw output을 완료처럼 보이게 한 경우).

## Light Brief

큰 작업은 아래 5-6줄 정도로 시작한다. scope 축소, AI 후보, raw/debug output, stub, product/eval 경계가 흔들리면 `제품 흐름` 한 줄을 더한다. 기본 출력 위치는 대화나 현재 작업 메모다. 별도 파일은 기록 위치 조건을 만족할 때만 만들고, PR/commit 근처 기록은 실제로 PR이나 commit을 다룰 때만 쓴다.

```text
왜 지금:
사용자 장면:
먼저 고를 slice:
제품 흐름(필요할 때만): 입력 -> 변환 -> 출력 / 넘지 말 선
이번 AC:
주의할 점:
남은 판단:
```

`이번 AC`는 기본 1-3개로 제한한다. 4개 이상이면 feature가 너무 커졌는지 먼저 의심하되, 숫자보다 한 사용자 장면이나 한 실패 유형으로 관찰 가능한지를 먼저 본다. AC를 줄인다는 이유로 그 behavior를 성립시키는 흐름을 자르지 않는다.

## 기존 spec을 구현할 때

기존 spec을 구현하기 전에는 해당 spec이 단독 기준인지, 상위 feature spec이나 앞뒤 하위 spec처럼 함께 봐야 할 참조 맥락이 있는지 짧게 확인한다. 목적은 관련 문서를 작업 목록으로 만드는 것이 아니라, 현재 spec이 제품 흐름 안에서 받는 입력과 넘기는 출력을 놓치지 않는 것이다.

짧게 확인할 질문:

- 현재 spec은 단독 기준인가, 상위/인접 spec의 입력/출력 계약을 짧게 봐야 하는가?
- 입력은 앞 단계 product artifact인가, fixture/seed인가?
- 출력은 뒤 단계가 소비할 계약인가, 화면 통과용 고정값인가?
- Non-goal로 뺀 것이 기술 충실도인가, 제품 흐름 자체인가?
- stub이 같은 계약을 통과시키는 test double인가, 실제 후보 생성 경로를 대체하는 완성 기능인가?
- raw/debug/API output 그대로 보여주기가 사용자가 읽는 결과로 변환하는 일을 대체하지 않는가?

spec의 자세한 읽기 순서, 용어 정의, examples는 `docs/specs/README.md`를 기준으로 한다. 다만 현재 작업에서 필요한 맥락만 짧게 보고, README나 examples를 hidden playbook, 현재 작업 queue, 선행 gate로 쓰지 않는다.

## 기록 위치

- `docs/specs/README.md`: spec 운영 기준, 용어, calibration examples의 원천.
- `docs/specs/*.md`: 여러 세션/작업으로 이어지는 제품 동작 기준. 작은 작업마다 만들지 않는다.
- `docs/decisions/*.md`: 이후 구현 방향에 영향을 줄 결정, 기각/보류한 방법론, tradeoff.
- `docs/implementation-notes/*.md`: 구현 중 반복해서 다시 볼 오해, drift, 경계 관찰.
- `docs/work-log.md`: 중요한 작업의 얇은 재진입 기록.
- commit/PR/test output: 작은 작업의 기본 기록 위치.

새 spec 파일은 같은 제품 동작 기준이 여러 작업으로 이어지거나, AC drift가 반복되거나, 검토 과정에서 정리된 사용자-facing 실패 유형이나 제품 기준이 다음 작업에서도 유지되어야 하거나, 사용자-facing 실패 유형을 분리해야 할 때만 만든다.

decision note는 방법론이나 구조를 채택/축소/기각/보류했거나, product-first와 spec/eval 운영 사이의 tradeoff를 정했거나, 나중에 다시 도전받을 선택일 때만 만든다.

## Runtime Smells

아래 신호가 보이면 멈추고 다시 좁히거나 사용자에게 확인한다.

- spec이 없으니 구현을 못 한다는 말이 나온다.
- 모든 작은 수정에 spec/log/eval을 붙이려 한다.
- 이번 AC가 사용자-visible behavior가 아니라 실행 순서표가 된다.
- 현재 spec/AC가 특정 fixture/seed 문장이나 값 맞추기로 좁아진다.
- 구현면 펼치기 없이 slice 후보가 작은 코드 TODO로 쪼개진다.
- `더 얇게`가 어떤 계약은 유지하고 어떤 기술 충실도만 줄이는지 없이 쓰인다.
- raw/debug/API output을 product result처럼 보여주려 한다.
- stub이나 deterministic adapter가 test double이 아니라 안 해도 되는 이유처럼 쓰인다.
- eval fixture, runner, expected output 준비만으로 product behavior를 확인했다고 말한다.
- archive된 SDD, examples, 과거 작업 메타를 현재 gate나 queue로 되살리려 한다.
- 아직 없는 run, proof, before/after를 완료된 것처럼 쓰려 한다.

## Metadata

- Source: TripProof repo-local skill.
- Input: 현재 TripProof 작업 요청, 관련 feature, 현재 코드/문서 상태.
- Output: 큰 작업 여부 판단, 이번 AC, 최소 brief, 기록 위치 제안, 위험 신호.
- Bridge: Claude 원천은 `.claude/skills/spec-driven`, Codex 브릿지는 `.codex/skills/spec-driven` symlink.
