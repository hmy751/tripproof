---
name: tripproof-spec-driven
description: TripProof repo 전용 light spec-driven 작업 루프. TripProof에서 큰 작업, AI 위임, AC(acceptance criteria) 선택, product-first/eval 관찰, 사람 판단 회수, spec/decision/work-log 기록 위치를 판단해야 할 때 사용한다. "TripProof spec-driven", "feature spec", "AC를 고르자", "spec으로 작업하자", "이 작업이 큰 작업인가", "문서가 실행을 잡아먹지 않게" 같은 요청에 트리거한다.
---

# TripProof Spec-driven

이 skill은 TripProof에서 spec-driven을 repo gate가 아니라 가벼운 작업 루프로 쓰게 한다. 목적은 구현 전에 사용자 장면, 경계, 확인 기준을 짧게 맞춰 사람과 AI가 같은 완료 조건을 보게 하는 것이다.

## Scope

- Source: TripProof repo-local skill.
- Input: 현재 TripProof 작업 요청, 관련 feature, 현재 코드/문서 상태.
- Output: 큰 작업 여부 판단, 이번 AC(acceptance criteria), 최소 brief, 기록 위치 제안, 위험 신호.
- Bridge: Claude 원천은 `.claude/skills/tripproof-spec-driven`, Codex 브릿지는 `.codex/skills/tripproof-spec-driven` symlink.

## 실행 우선순위

현재 사용자 요청의 범위가 먼저다. read-only/review 요청이면 판단만 보고하고 파일을 고치지 않는다. 구현 요청이면 작은/큰 작업을 판단한 뒤 진행한다. 이 skill은 새 spec 파일 생성, 문서 수정, stage/commit 권한을 자동으로 부여하지 않는다.

## 먼저 판단할 것

큰 작업이면 light brief를 남긴다. 작은 작업이면 바로 실행한다.

큰 작업 신호:

- 사용자 flow가 바뀐다.
- AI 위임 범위가 크다.
- AC가 애매하다.
- 실패 유형 분해가 필요하다.
- 다음 세션이나 다른 사람이 이어받아야 한다.
- product contract, evidence state, human review, card 승격, eval 관찰 대상이 바뀐다.

작은 작업 신호:

- 오타, 문구, 좁은 UI 조정.
- 기존 AC 안에서 닫히는 작은 bugfix.
- 단일 파일의 좁은 refactor.
- 이미 선택된 feature의 테스트 보강.
- 실패해도 원인과 판단이 흐려지지 않는다.

큰 작업이 큰 feature면, AC로 바로 좁히기 전에 구현면을 먼저 펼친다. 업로드, 텍스트 추출, 청크, 후보 생성, 근거, 답변 UI, 카드, 대시보드, guard 같은 구현면을 꺼내 보고, 그 면을 얇게 관통하는 slice 후보를 본다. 불확실하다고(PDF/OCR/LLM) 미리 Non-goals로 자르지 않는다. 이미 경로가 좁은 작은 spec이나 bugfix라면 생략할 수 있고, 생략할 때는 왜 생략하는지 한 줄로 둔다.

LLM 불확실성은 데모로 대체하지 않는다. 줄일 수 있는 것은 provider 품질, ingestion 충실도, 처리 범위이지, `자료 -> 후보/evidence -> 상태 -> 화면`으로 이어지는 product causality가 아니다. 여기서 product causality는 자료가 바뀌면 답도 바뀌고, evidence quote가 없으면 `근거 있음`이 될 수 없는 인과다. deterministic baseline이나 stub은 같은 계약을 통과시키는 test double일 수 있지만, product proof의 주인공이 되면 안 된다.

## Light Brief

큰 작업은 아래 5-6줄 정도로 시작한다. 기본 출력 위치는 대화나 현재 작업 메모다. 별도 파일은 기록 위치 조건을 만족할 때만 만들고, PR/commit 근처 기록은 실제로 PR이나 commit을 다룰 때만 쓴다. 큰 feature라면 구현면과 slice 후보를 본 뒤 `먼저 고를 slice`를 같이 적는다.

```text
왜 지금:
사용자 장면:
먼저 고를 slice:
이번 AC:
주의할 점:
남은 판단:
```

`이번 AC`는 기본 1-3개로 제한한다. 4개 이상이면 feature가 너무 커졌는지 먼저 의심하되, 숫자보다 한 사용자 장면이나 한 실패 유형으로 관찰 가능한지를 먼저 본다.

예시:

```text
왜 지금: 첫 product proof를 숙소 체크인 준비 장면으로 좁혀, 문서/하네스가 아니라 화면 동작으로 확인한다.
사용자 장면: 사용자가 자료함 전체에 "체크인은 몇 시부터, 늦게 도착하면?"을 묻는다.
먼저 고를 slice: sanitized material text를 grounded extractor에 넣고, 체크인 시작 시간은 quote 기반 `근거 있음`, 늦은 도착 조건은 quote 부재 기반 `근거 부족`으로 채팅 화면과 인라인 근거까지 잇는다.
이번 AC: 체크인 시작 시간 `근거 있음`; 늦은 도착 조건 `근거 부족` + `직접 확인`; 카드 승격 경계
주의할 점: 자료에 없는 늦은 도착 조건을 AI가 일반 지식으로 보충하거나, 후보 답변이 confirmed 카드처럼 올라가면 안 된다.
남은 판단: 늦은 도착 조건과 직접 확인 카드를 같은 구현 턴에 닫을지 다음 slice로 뺄지 작업 brief에서 다시 고른다.
```

이 예시는 calibration이다. 그대로 다음 작업 목록이 아니라, 이번 작업에서 AC를 고르는 감각을 맞추기 위한 기준이다.

## Slice와 이번 AC 선택

spec은 작업을 만들지 못하게 한다. 이미 선택한 사용자 장면을 좁히는 데만 쓴다.

아래 흐름은 큰 feature에서 판단이 흐려질 때 참고하는 흐름이며, 작은 작업의 필수 절차가 아니다.

좋은 흐름:

```text
사용자 장면 선택
-> Goal / Rules / Non-goals를 짧게 확인
-> 구현면 펼치기
-> 현재 코드와 비교
-> slice 후보를 필요한 만큼 나열
-> 먼저 고를 slice 1개 선택
-> 이번 작업 brief와 관찰할 AC 정리
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
- AC가 반복해서 drift된다.
- AI 위임 결과가 제품 동작 기준으로 남아 다음 세션이 이어받아야 한다.
- 사용자-facing 실패 유형을 분리해야 한다.

구현면을 펼친 뒤 나온 후보가 크고 독립적이면 별도 feature spec(`01` → `01-01`)으로 나눌 수 있다. 대부분의 후보는 slice라 한 feature 안에서 순서대로 짓는다.

decision note는 다음 중 하나일 때만 만든다.

- 어떤 방법론이나 구조를 채택/축소/기각/보류했다.
- product-first와 spec/eval 운영 사이의 tradeoff를 정했다.
- 나중에 다시 도전받을 선택이다.

## feature spec 읽기 순서

feature spec은 처음 읽는 사람이 빠르게 제품 동작을 잡을 수 있어야 한다.

1. 사용자 장면: 어떤 자료를 넣고 무엇을 묻는가.
2. Goal: 이 feature가 끝났다고 말할 사용자-visible 결과는 무엇인가.
3. Rules: 그 결과를 만들 때 AI, 화면, 상태가 넘지 말아야 할 경계는 무엇인가.
4. Non-goals: 이 feature를 작게 유지하기 위해 의도적으로 빼는 것은 무엇인가.
5. 상태 언어: 사용자에게 보이는 말과 내부 상태 축의 관계.
6. 구현면 펼치기: 큰 feature라면 어떤 큰 구현면을 지나야 하는가.
7. Slice 후보: 펼친 구현면을 관통하는 product path 후보는 무엇인가.
8. 먼저 고를 slice: 이번 구현에서 화면까지 이을 경로 하나는 무엇인가.
9. 이번 AC / 확인 방법: 어떤 product behavior를 관찰할 것인가.

세부 기준, entry point, Tests / scenario(사례), eval 관찰 기준은 그 뒤에 둔다. scenario는 작업 순서표가 아니라 AC를 확인할 때 꺼내는 대표 상황으로 읽는다.

feature spec이 전체 기준을 담고 있어도, 현재 구현 작업은 별도 brief에서 먼저 고를 slice와 관찰할 AC 1-3개를 다시 고른다. 전체 기준의 확인 방법은 feature가 언젠가 닫혔다고 말하기 위한 기준이지, 모든 작업의 기본 체크리스트가 아니다.

## 스펙 구현 전 참조 맥락 확인

스펙을 구현하기 전에는 먼저 해당 스펙이 단독 기준인지, 상위 feature spec이나 앞뒤 하위 스펙처럼 함께 읽어야 할 참조 맥락이 있는지 확인한다. 참조 맥락이 있으면 부모 스펙의 사용자 장면, 먼저 고를 slice, 이번 AC와 인접 스펙의 입력/출력 계약을 짧게 본다. 목적은 관련 문서를 작업 목록으로 만드는 것이 아니라, 현재 구현할 스펙이 product path 안에서 어떤 입력을 받고 어떤 출력을 넘기는지 확인하는 것이다. gate가 아니라 짧은 context pass다.

짧게 확인할 질문:

- 현재 스펙은 단독 구현 기준인가, 상위/인접 스펙을 참조해야 하는가?
- 입력은 앞 단계에서 온 product artifact인가, fixture/seed인가?
- 출력은 뒤 단계가 소비할 계약인가, 화면을 통과시키기 위한 고정값인가?
- Non-goal로 뺀 것이 기술 충실도인가, product causality 자체인가?
- deterministic/stub이 같은 계약을 통과시키는 test double인가, 실제 후보 생성 경로를 대체하는 완성 기능인가?

냄새 신호:

- 현재 스펙의 AC가 특정 fixture 문장/값 매칭으로 바뀐다.
- 앞 단계 산출물 대신 원본 fixture를 직접 훑는다.
- 뒤 단계가 소비할 계약보다 일단 보이는 답이 먼저 생긴다.
- `LLM은 나중에`가 `retrieval/grounding 계약도 나중에`로 미끄러진다.

## TripProof의 기본 경계

- product가 먼저다. eval은 product behavior를 관찰한다.
- product-first는 implementation-first가 아니다. spec/brief는 제품 동작과 이번 AC를 짧게 맞추기 위한 판단 도구다. 다만 승인 gate, 긴 작업 목록, eval 선행 조건으로 커지지 않게 둔다.
- spec은 승인권, 현재 작업 queue, 선행 gate가 아니다.
- feature 단위 AC는 `docs/prd.md`와 baseline 코드/test가 소유한다. feature마다 AC를 재서술하는 새 spec을 자동으로 만들지 않는다.
- AI output은 목표가 아니라 후보다. 채택/기각은 사람이 판단한다.
- 회사 요구는 역량 프레임으로만 연결한다. product 동기로 역수입하지 않는다.
- full SDD, toolkit 도입, 모든 작업 spec화는 기본값이 아니다. 지금 기본은 light brief다.
- 폐기된 작업 메타나 부산물을 proof로 되살리지 않는다.

## 냄새 신호

멈추고 다시 좁힌다:

- spec이 없으니 구현을 못 한다는 말이 나온다.
- eval fixture/runner가 product보다 먼저 커진다.
- 이번 AC가 실행 순서표가 된다.
- 구현면 펼치기 없이 slice 후보가 작은 코드 TODO로 쪼개진다.
- `ingest`, `chat`, `card`, `dashboard` 같은 큰 면이 사라지고 `seed`, `button`, `type` 같은 작은 접점만 남는다.
- AC와 slice가 같은 목록처럼 합쳐진다.
- stub이 slice를 통과시키는 임시 구조가 아니라 안 해도 되는 이유처럼 쓰인다.
- LLM hallucination, PDF/OCR 복잡도, 민감정보 위험을 이유로 `seed -> hard-coded answer -> 화면`만 만들고 product proof라고 부른다.
- deterministic adapter가 grounded extractor 계약의 test double이 아니라, 실제 후보 생성 경로를 대신하는 완성 기능처럼 쓰인다.
- `real LLM은 뒤로 둔다`가 provider 품질 보류가 아니라 AI 후보/evidence 계약 자체를 닫는 말로 쓰인다.
- 모든 작은 수정에 spec/log/eval을 붙이려 한다.
- 공고 키워드나 방법론 이름이 사용자 장면보다 먼저 나온다.
- 현재 코드 비교가 light brief 없이 바로 파일 수정 목록으로 바뀐다.
- "spec은 나중에 정리하고 일단 구현"이 큰 작업의 기본 흐름처럼 적용된다.
- 한 필드가 실데이터로 끝까지 돌기 전에 부품 목업을 따로 만들기 시작한다.
- 아직 없는 run, proof, before/after를 완료된 것처럼 쓰려 한다.

## 권장 첫 슬라이스 감각

이 섹션은 현재 첫 product proof를 고를 때의 calibration이다. 현재 작업 queue가 아니며, 다른 feature에는 숙소 체크인 예시가 아니라 같은 판단축만 옮긴다.

TripProof의 첫 product proof는 기능 전체보다 실패 유형 단위로 좁힌다.

예:

```text
예약 확인서/호스트 안내를 넣는다
-> 체크인 시간은 근거 있음으로 답한다
-> 늦은 도착 조건은 근거 부족으로 멈춘다
-> 사용자가 직접 확인 카드로 올린다
```

큰 feature를 펼친 뒤에는 한 slice씩 짓는다. 기본 좁힘 순서는 `구현면 펼치기 -> slice 후보 -> 먼저 고를 slice`다.

구현면은 넓게 펼치는 지도다. 예: 자료 입력/ingest, AI 후보 생성, 정규화/상태 언어, 채팅 답변, 인라인 근거, 카드 초안, 직접 확인, 대시보드 출처, 민감정보 guard.

slice 후보는 그 구현면을 얇게 관통하는 product path다. 예:

- 체크인 시작 시간 답변: 자료 입력 / AI 후보 / 정규화 / 채팅 / 인라인 근거를 지나 `근거 있음` 답변을 화면에 보인다.
- 늦은 도착 조건 근거 부족: 자료에 값이 없으면 채팅 답변이 값을 만들지 않고 `근거 부족`으로 멈춘다.
- 답변에서 카드 초안으로: 근거 있는 답변을 카드 초안으로 올리기 전 검토한다.
- 근거 부족에서 직접 확인 카드로: 사용자가 직접 채운 값이 대시보드에서 `직접 확인`으로 보인다.
- 민감정보 자동 카드 제외: 예약번호/출입코드가 자동 카드 후보가 되지 않는다.

먼저 고를 slice는 후보 중 이번 구현에서 화면까지 이을 하나다. 이때 실제로 닫는 면과 stub으로 받치는 면을 함께 적는다. 예: 체크인 질문 답변을 먼저 고르고, sanitized material text와 grounded extractor 계약으로 `자료 -> extractor 후보 + evidence quote -> 상태 -> 채팅 답변 -> 인라인 근거`를 잇는다. 실제 Gmail/PDF/OCR ingestion처럼 이번에 깊게 다루지 않는 면은 기술 충실도로 뒤로 둘 수 있다. 자료가 바뀌면 답도 바뀌고, evidence quote가 없으면 `근거 있음`이 될 수 없어야 한다.

- 각 slice는 한 필드, 한 상태, 한 실패 유형을 화면까지 통과시킨다. 여기서 "끝까지"는 화면에 닿는 깊이지, 모든 부품을 완성한다는 뜻이 아니다.
- 완료 기준은 컴포넌트가 아니라 화면 동작이다.
- commit을 만들 때 필요하면 닫은 slice와 AC의 연결을 본문에 남긴다 (예: `... (AC #1)`).
