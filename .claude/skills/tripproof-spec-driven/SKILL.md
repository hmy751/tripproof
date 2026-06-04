---
name: tripproof-spec-driven
description: TripProof repo 전용 light spec-driven 작업 루프. TripProof에서 큰 slice, AI 위임, acceptance 선택, product-first/eval 관찰, 사람 판단 회수, spec/decision/work-log 기록 위치를 판단해야 할 때 사용한다. "TripProof spec-driven", "slice brief", "acceptance를 고르자", "spec으로 작업하자", "이 작업이 큰 slice인가", "문서가 실행을 잡아먹지 않게" 같은 요청에 트리거한다.
---

# TripProof Spec-driven

이 skill은 TripProof에서 spec-driven을 repo gate가 아니라 가벼운 작업 루프로 쓰게 한다. 목적은 구현 전에 사용자 장면, 경계, 확인 기준을 짧게 맞춰 사람과 AI가 같은 완료 조건을 보게 하는 것이다.

## Scope

- Source: TripProof repo-local skill.
- Input: 현재 TripProof 작업 요청, 관련 product slice, 현재 코드/문서 상태.
- Output: 큰 slice 여부 판단, 이번 확인 기준(selected acceptance), 최소 brief, 기록 위치 제안, 위험 신호.
- Bridge: Claude 원천은 `.claude/skills/tripproof-spec-driven`, Codex 브릿지는 `.codex/skills/tripproof-spec-driven` symlink.

## 먼저 판단할 것

큰 slice이면 light brief를 남긴다. 작은 작업이면 바로 실행한다.

큰 slice 신호:

- 사용자 flow가 바뀐다.
- AI 위임 범위가 크다.
- acceptance가 애매하다.
- 실패 유형 분해가 필요하다.
- 다음 세션이나 다른 사람이 이어받아야 한다.
- product contract, evidence state, human review, card 승격, eval 관찰 대상이 바뀐다.

작은 작업 신호:

- 오타, 문구, 좁은 UI 조정.
- 기존 acceptance 안에서 닫히는 작은 bugfix.
- 단일 파일의 좁은 refactor.
- 이미 선택된 slice의 테스트 보강.
- 실패해도 원인과 판단이 흐려지지 않는다.

## Light Brief

큰 slice는 아래 5줄 정도로 시작한다. 별도 파일이 아니라 대화, 작업 메모, PR/commit 근처에 있어도 된다.

```text
왜 지금:
사용자 장면:
이번 확인 기준(selected acceptance):
주의할 점:
남은 판단:
```

`selected acceptance`는 기본 1-3개로 제한한다. 4개 이상이면 slice가 너무 커졌는지 먼저 의심한다.

예시:

```text
왜 지금: 첫 product proof를 숙소 체크인 준비 장면으로 좁혀, 문서/하네스가 아니라 화면 동작으로 확인한다.
사용자 장면: 사용자가 자료함 전체에 "체크인은 몇 시부터, 늦게 도착하면?"을 묻는다.
이번 확인 기준(selected acceptance): 체크인 시작 시간 `근거 있음`; 늦은 도착 조건 `근거 부족` + `직접 확인`; 카드 승격 경계
주의할 점: 자료에 없는 늦은 도착 조건을 AI가 일반 지식으로 보충하거나, 후보 답변이 confirmed 카드처럼 올라가면 안 된다.
남은 판단: P0는 실제 PDF/OCR/LLM adapter 없이 synthetic text와 현재 product entry point로 시작한다.
```

이 예시는 calibration이다. 그대로 다음 작업 목록이 아니라, 이번 slice에서 acceptance를 고르는 감각을 맞추기 위한 기준이다.

## 이번 확인 기준 선택

spec은 작업을 만들지 못하게 한다. 이미 선택한 사용자 장면을 좁히는 데만 쓴다.

좋은 흐름:

```text
사용자 장면 선택
-> 이번 확인 기준(selected acceptance) 1-3개 선택
-> product 구현
-> 수동 확인 또는 테스트 관찰
-> 필요한 판단만 기록
```

나쁜 흐름:

```text
spec 읽기
-> spec 항목 전체를 작업 목록화
-> 구현 순서표 만들기
-> 문서/하네스가 product보다 앞섬
```

## 기록 위치

- `docs/specs/README.md`: spec을 어떻게 쓸지에 대한 짧은 운영 규칙.
- `docs/specs/*.md`: 여러 세션/작업으로 이어지는 제품 동작 기준. 작은 작업마다 만들지 않는다.
- `docs/decisions/*.md`: 이후 구현 방향에 영향을 줄 결정, 기각/보류한 방법론, tradeoff.
- `docs/work-log.md`: 중요한 작업의 얇은 재진입 기록.
- commit/PR/test output: 작은 작업의 기본 기록 위치.

새 spec 파일은 다음 중 하나일 때만 만든다.

- 같은 제품 동작 기준이 여러 작업으로 이어진다.
- acceptance가 반복해서 drift된다.
- AI 위임 결과를 다음 세션이 이어받아야 한다.
- 사용자-facing 실패 유형을 분리해야 한다.

decision note는 다음 중 하나일 때만 만든다.

- 어떤 방법론이나 구조를 채택/축소/기각/보류했다.
- product-first와 spec/eval 운영 사이의 tradeoff를 정했다.
- 나중에 다시 도전받을 선택이다.

## Slice 문서 권장 읽기 순서

slice 문서는 처음 읽는 사람이 빠르게 제품 동작을 잡을 수 있어야 한다.

1. 사용자 장면: 어떤 자료를 넣고 무엇을 묻는가.
2. Goal / Rules: 이번 slice가 끝났다고 말할 목표와 지켜야 할 경계는 무엇인가.
3. Non-goals: 이번 slice를 작게 유지하기 위해 의도적으로 빼는 것은 무엇인가.
4. 상태 언어: 사용자에게 보이는 말과 내부 상태 축의 관계.
5. 이번 확인 기준(selected acceptance): 지금 작업에서 고를 1-3개 장면.
6. 확인 방법: 테스트나 수동 product 확인으로 관찰할 것.

세부 기준, entry point, Tests / 관찰 케이스, eval 관찰 기준은 그 뒤에 둔다. 관찰 케이스는 작업 순서표가 아니라 acceptance를 확인할 때 꺼내는 대표 상황으로 읽는다.

slice 문서가 P0 전체 기준을 담고 있어도, 현재 구현 작업은 별도 brief에서 `selected acceptance` 1-3개를 다시 고른다. 전체 기준의 확인 방법은 slice가 언젠가 닫혔다고 말하기 위한 기준이지, 모든 작업의 기본 체크리스트가 아니다.

## TripProof의 기본 경계

- product가 먼저다. eval은 product behavior를 관찰한다.
- spec은 승인권, 현재 작업 queue, 선행 gate가 아니다.
- AI output은 목표가 아니라 후보다. 채택/기각은 사람이 판단한다.
- 회사 요구는 역량 프레임으로만 연결한다. product 동기로 역수입하지 않는다.
- full SDD, toolkit 도입, 모든 작업 spec화는 기본값이 아니다. 지금 기본은 light brief다.
- 폐기된 작업 메타나 부산물을 proof로 되살리지 않는다.

## 냄새 신호

멈추고 다시 좁힌다:

- spec이 없으니 구현을 못 한다는 말이 나온다.
- eval fixture/runner가 product보다 먼저 커진다.
- selected acceptance가 실행 순서표가 된다.
- 모든 작은 수정에 spec/log/eval을 붙이려 한다.
- 공고 키워드나 방법론 이름이 사용자 장면보다 먼저 나온다.
- 아직 없는 run, proof, before/after를 완료된 것처럼 쓰려 한다.

## 권장 첫 slice 감각

TripProof의 첫 product proof는 기능 전체보다 실패 유형 단위로 좁힌다.

예:

```text
예약 확인서/호스트 안내를 넣는다
-> 체크인 시간은 근거 있음으로 답한다
-> 늦은 도착 조건은 근거 부족으로 멈춘다
-> 사용자가 직접 확인 카드로 올린다
```

`conflict`, `sensitive`, 실제 ingestion, LLM adapter, metric threshold는 product 흐름이 돈 뒤 별도 slice로 여는 편이 안전하다.
