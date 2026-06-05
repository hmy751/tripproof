# Specs

현재 specs 운영 기준은 이 README다. spec-driven 구조를 light loop로 낮춘 배경 결정은 `docs/decisions/2026-06-03-light-spec-driven-loop/`를 본다.

`docs/specs/`에는 여러 작업으로 이어지는 제품 동작 기준만 둔다. 과거의 `00-spec-driven-development.md`는 `docs/archive/spec-driven/00-spec-driven-development.md`에 보관된 스냅샷이며, 현재 작업 queue나 절차 gate가 아니다.

작은 수정마다 spec을 만들 필요는 없다. 나중에 다시 봐야 할 목표, 제약, 결정, 남은 쟁점만 짧게 남긴다.

## 처음 읽는 법

TripProof의 light spec-driven은 구현 전에 사용자 장면, 경계, 확인 기준을 짧게 맞춰 사람과 AI가 같은 완료 조건을 보게 하는 작업 루프다.

spec은 승인 gate나 작업 목록이 아니라, 큰 작업에서 무엇을 통과로 볼지와 무엇을 Non-goals로 둘지를 맞추는 얇은 기준이다. 미리 써서 막는 gate가 아니라 개발하며 자라는 기준이라, 큰 feature도 작은 보완도 spec이 된다. 처음 읽을 때는 아래 순서로 본다.

1. **사용자 장면**: 사용자가 어떤 자료를 넣고 무엇을 물어보는가.
2. **Goal / Rules**: 이 feature가 끝났다고 말할 목표와 지켜야 할 경계는 무엇인가.
3. **Non-goals**: 중요하지 않아서가 아니라, 이 feature를 작게 유지하기 위해 의도적으로 빼는 것은 무엇인가.
4. **상태 언어**: 사용자가 화면에서 보게 될 말. 내부 타입명은 그 뒤에 본다.
5. **이번 AC**: 지금 작업에서 실제로 확인할 1-3개의 제품 동작은 무엇인가.
6. **확인 방법**: 선택한 AC가 통과했는지 어떻게 관찰할 것인가.

용어는 이렇게 쓴다. 표준 spec-driven 용어를 쓰고, 맞는 표준어가 없을 때만 우리말을 둔다.

| 용어 | 뜻 |
| --- | --- |
| feature | spec이 다루는 기능 단위. 크기는 고정하지 않으며, 한 사용자 장면을 끝까지 통과시키는 단위가 기본이다. 예: 숙소 체크인 확인 |
| slice | feature를 짓는 빌드 단계. 한 필드를 실데이터로 자료 → AI → 상태 → 화면까지 끝까지 통과시킨다 |
| 부품 | feature를 이루는 구현 조각. 이번 slice에서 짓지 않는 부품은 stub으로 둔다 |
| scenario (사례) | feature에서 확인할 구체 상황. 나중에 AC를 확인할 때 꺼내는 대표 사례지 작업 순서표가 아니다 |
| acceptance criteria (AC) | feature의 통과 조건. 이번 작업에서 확인할 1-3개를 "이번 AC"로 고른다 |
| user scene (사용자 장면) | 사용자가 실제로 처한 상황, 입력 자료, 질문 |
| check method (확인 방법) | 테스트, 수동 확인, 화면 관찰처럼 완료를 확인하는 방법 |

작업 크기는 따로 가른다: 실패했을 때 원인과 판단이 흐려질 만한 **큰 작업**이면 아래 brief를 남기고, **작은 작업**이면 바로 진행한다.

## 문서 경계

spec에는 현재 repo에서 확인 가능한 목표, 제약, 결정, 열린 질문, 검증 후보만 남긴다.

feature 단위 통과 기준(AC)은 새 spec이 자동으로 다시 쓰지 않는다. 이미 `docs/prd.md`와 baseline 코드/test가 나눠 소유한 기준이 있으면, 새 spec은 그 기준을 재서술하기보다 필요한 만큼 가리킨다.

아직 없는 product flow, eval run, before/after, metric, public case study를 완료된 proof처럼 쓰지 않는다. repo 밖 개인 자료, 공고/포트폴리오 맥락, 대화 원문, 도구 이름도 product 근거처럼 남기지 않는다.

TripProof의 기본 방향은 product-first다. eval은 product behavior를 호출하고 관찰한다. product code가 eval fixture, run artifact, metric output에 의존하게 만들지 않는다.

지금 만들지 않을 문서 예시:

- 실제 run 없는 eval 결과표
- metric threshold 확정 문서
- 증거 없는 public before/after case study
- 작업량 메타를 product proof처럼 보이게 하는 운영 로그

## Light spec-driven loop

TripProof의 spec-driven은 문서 gate가 아니라 큰 작업을 작게 잡기 위한 작업 루프다.

큰 작업이면 작업 시작 전에 5줄 정도의 brief를 둔다.

```text
왜 지금:
사용자 장면:
이번 AC:
주의할 점:
남은 판단:
```

큰 작업의 기준은 실패했을 때 원인과 판단이 흐려지는가다. 사용자 flow가 바뀌거나, AI 위임 범위가 크거나, AC가 애매하거나, 실패 유형 분해가 필요하거나, 다음 세션이 이어받아야 하면 큰 작업으로 본다.

작은 작업은 별도 spec 없이 바로 진행한다. 오타, 좁은 UI 조정, 기존 AC 안의 bugfix, 작은 refactor, 테스트 보강은 commit, PR, test output 근처에 남기는 것으로 충분하다.

`이번 AC`는 기본 1-3개로 제한한다. spec은 작업을 만들지 않고, 이미 선택한 사용자 장면을 좁히는 데만 쓴다. 큰 feature를 slice로 나눠 적더라도 그 목록은 진행 메모지 통과 기준이 아니다. 비어 있어도 코딩을 막지 않고, 별도 work-map 파일은 만들지 않는다.

새 spec 파일은 여러 세션으로 이어지는 제품 동작 기준이 필요하거나, AC drift가 반복되거나, 사용자-facing 실패 유형을 분리해야 할 때만 만든다.

권장 형식:

```md
# Feature 이름

이 문서는 전체 작업 목록이 아니라, 사용자 장면과 경계, 확인 기준을 맞추기 위한 제품 동작 기준이다.

## 한눈에 보기

### 사용자 장면

### Goal

### Rules

### Non-goals

### 상태 언어

### 이번 AC

### 확인 방법

## 상세 기준

### Flow

### Data / State

### Tests / scenario(사례)

### 보류 질문
```

이 형식은 빈칸을 모두 채우라는 템플릿이 아니다. 각 항목은 다음 판단을 보정하기 위한 calibration sample처럼 읽는다.

| 항목 | 관통 개념 | 좋음 | 나쁨 |
| --- | --- | --- | --- |
| 사용자 장면 | 기능명이 아니라 실제 사용 순간을 잡는다. | 예약 확인서와 호스트 안내를 넣고 체크인 시간과 늦은 도착 조건을 묻는다. | 숙소 정보 추출 기능을 만든다. |
| Goal | 끝났다고 말할 핵심 결과를 좁힌다. | 체크인 시작 시간은 근거와 함께 답하고, 늦은 도착 조건이 없으면 멈춘다. | 숙소 체크인 AI를 완성한다. |
| Rules | AI와 화면이 넘지 말아야 할 경계를 둔다. | 자료 밖 일반 지식으로 답을 보충하지 않는다. | 가능하면 친절하고 자세하게 답한다. |
| Non-goals | 중요하지 않아서가 아니라 이 feature를 작게 유지하기 위해 뺀다. | 실제 PDF/OCR ingestion은 이번 기준 밖이다. | 나중에 할 일: OCR, LLM, eval dashboard. |
| 이번 AC | 전체 spec이 아니라 이번 작업에서 볼 1-3개 동작을 고른다. | 체크인 시간 `근거 있음`, 늦은 도착 조건 `근거 부족`, 직접 확인 카드 경계. | 체크인 feature 전체 구현, 모든 scenario 처리. |
| scenario(사례) | 나중에 확인할 대표 상황이다. 작업 순서표가 아니다. | "늦은 도착 조건이 자료에 없음"을 missing scenario로 둔다. | P0-A부터 P0-E까지 순서대로 구현한다. |

작게 남길 때는 맨 위 5줄 brief만 써도 충분하다.

좋은 spec은 "해야 할 일"을 많이 늘리지 않는다. 대신 이번 사용자 장면에서 무엇을 통과해야 하고, 무엇을 아직 하지 않는지 선명하게 만든다.

feature spec이 전체 기준을 담고 있어도, 각 구현 작업은 다시 5줄 brief로 `이번 AC` 1-3개를 고른 뒤 시작한다.

짧은 brief 예시:

- 좋음: "이번 AC는 체크인 시작 시간 `근거 있음`, 늦은 도착 조건 `근거 부족`, 직접 확인 카드 경계다." — 사용자 장면 안에서 확인할 동작을 좁힌다.
- 나쁨: "체크인 feature 전체 구현, eval 추가, ingestion 개선, 카드 UI 정리, 모든 scenario 처리." — spec 전체를 작업 목록으로 바꾼다.

큰 feature를 slice로 펼치고 한 단계씩 개발하는 방법은 `tripproof-spec-driven` skill을 따른다.
