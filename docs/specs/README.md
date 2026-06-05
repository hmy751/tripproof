# Specs

현재 specs 운영 기준은 이 README다. spec-driven 구조를 light loop로 낮춘 배경 결정은 `docs/decisions/2026-06-03-light-spec-driven-loop/`를 본다.

`docs/specs/`에는 여러 작업으로 이어지는 제품 동작 기준만 둔다. 과거의 `00-spec-driven-development.md`는 `docs/archive/spec-driven/00-spec-driven-development.md`에 보관된 스냅샷이며, 현재 작업 queue나 절차 gate가 아니다.

작은 수정마다 spec을 만들 필요는 없다. 나중에 다시 봐야 할 목표, 제약, 결정, 남은 쟁점만 짧게 남긴다.

## 처음 읽는 법

TripProof의 light spec-driven은 구현 전에 사용자 장면, 경계, 확인 기준을 짧게 맞춰 사람과 AI가 같은 완료 조건을 보게 하는 작업 루프다.

spec은 승인 gate나 작업 목록이 아니라, 큰 작업에서 무엇을 통과로 볼지와 무엇을 Non-goals로 둘지를 맞추는 얇은 기준이다. 미리 써서 막는 gate가 아니라 개발하며 자라는 기준이라, 큰 feature도 작은 보완도 spec이 된다. 처음 읽을 때는 아래 순서로 본다.

1. **사용자 장면**: 사용자가 어떤 자료를 넣고 무엇을 물어보는가.
2. **Goal**: 이 feature가 끝났다고 말할 사용자-visible 결과는 무엇인가.
3. **Rules**: 그 결과를 만들 때 AI, 화면, 상태가 넘지 말아야 할 경계는 무엇인가.
4. **Non-goals**: 중요하지 않아서가 아니라, 이 feature를 작게 유지하기 위해 의도적으로 빼는 것은 무엇인가.
5. **상태 언어**: 사용자가 화면에서 보게 될 말. 내부 타입명은 그 뒤에 본다.
6. **이번 AC**: 지금 작업에서 실제로 확인할 1-3개의 제품 동작은 무엇인가.
7. **확인 방법**: 선택한 AC가 통과했는지 어떻게 관찰할 것인가.

용어는 이렇게 쓴다. 표준 spec-driven 용어를 쓰고, 맞는 표준어가 없을 때만 우리말을 둔다.

| 용어 | 뜻 |
| --- | --- |
| feature | spec이 다루는 기능 단위. 크기는 고정하지 않으며, 한 사용자 장면을 끝까지 통과시키는 단위가 기본이다. 예: 숙소 체크인 확인 |
| slice | feature를 짓는 빌드 단계. 한 필드만 실제 데이터로 자료 → AI → 상태 → 화면까지 통과시키는 좁고 깊은 경로다. 여기서 "끝까지"는 화면에 닿는 깊이를 뜻하며, 모든 부품을 완성한다는 뜻이 아니다 |
| 부품 | feature를 이루는 구현 조각. 이번 slice가 실제로 만들지 않는 부품과 다른 필드는 stub으로 두고, slice는 그 stub 위에 필요한 경로만 잇는다 |
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

### Spec이 보존해야 할 판단

spec은 빈칸을 채우는 문서 양식이 아니라, 다음 작업자가 사용자 장면과 경계, 확인 기준을 다시 잡을 수 있게 하는 calibration sample이다. 아래 항목은 필요할 때 붙잡는 판단 질문이지, 모든 spec에 같은 순서와 같은 밀도로 들어가야 하는 템플릿이 아니다.

- **사용자 장면**: 기능명이 아니라 사용자가 어떤 자료를 넣고 어떤 판단을 하려는 순간인지 쓴다. 좋은 예는 "예약 확인서와 호스트 안내를 넣고 체크인 시간과 늦은 도착 조건을 묻는다"이고, 나쁜 예는 "숙소 정보 추출 기능"처럼 구현명만 남기는 것이다.
- **Goal**: 끝났다고 말할 사용자-visible 결과를 좁힌다. 좋은 예는 "체크인 시작 시간은 근거와 함께 답하고, 늦은 도착 조건이 없으면 `근거 부족`으로 멈춘다"이다. 나쁜 예는 "숙소 체크인 AI를 완성한다"처럼 완료 기준이 커지는 것이다.
- **Rules**: Goal을 만들 때 AI/화면/상태가 넘지 말아야 할 경계를 둔다. 좋은 예는 "자료 밖 일반 지식으로 답을 보충하지 않는다"이다. 나쁜 예는 "가능하면 친절하고 자세하게 답한다"처럼 안전 경계가 취향 문구로 흐르는 것이다.
- **Non-goals**: 덜 중요해서 버리는 목록이 아니라, 이번 feature나 slice의 통과 판단에서 제외한 범위다. "모르는 것"과 "이번에 하지 않는 것"을 같은 말로 두지 않는다.
- **상태 언어**: 사용자가 화면에서 보는 말을 먼저 둔다. 내부 타입명은 그 뒤에 매핑한다. `근거 부족` 답변도 사람이 값을 채워 올리면 `직접 확인` 카드가 될 수 있다는 식으로 상태 축과 결정 축을 섞지 않는다.
- **현재 코드와 이번 slice**: 부품을 펼치는 이유는 작업표를 만들기 위해서가 아니라 현재 코드와 비교해 이미 되는 것, 이번에 stub으로 둘 것, 사용자 장면을 통과시키려면 이어야 할 부분을 보기 위해서다. slice는 한 필드를 `자료 -> AI/adapter -> 상태 -> 화면`까지 잇는 vertical path이지, 부품 완성표가 아니다.
- **이번 AC**: 전체 feature가 아니라 이번 작업에서 관찰할 1-3개 product behavior다. AC 수는 확인할 동작 수를 제한하지, 그 동작을 화면까지 잇는 데 필요한 구현면 수를 제한하지 않는다.
- **확인 방법**: 완료 여부는 문서가 아니라 제품 동작으로 확인한다. 좋은 확인은 화면에서 상태 문구, 근거, 카드 승격 경계를 보는 것이고, 나쁜 확인은 spec 항목이 모두 채워졌는지만 보는 것이다.

### Non-goals / 구현면 / slice

Non-goals는 선택한 사용자 장면을 통과시키는 데 필요한 경로를 끊는 장치가 아니다. 실제 PDF/OCR parser, full LLM provider, 모든 필드, eval dashboard처럼 확장 깊이와 충실도는 이번 slice 밖으로 둘 수 있다. 하지만 그 경우에도 자료함에서 들어온 대체 입력, deterministic adapter, stub state처럼 한 필드가 화면까지 닿게 하는 경로는 살아 있어야 한다.

구현면 펼치기는 제외할 것을 찾는 절차가 아니라 현재 코드와 비교해 이번 slice를 고르는 재료다. `실제 PDF/OCR ingestion은 이번 기준 밖`이라는 말은 `자료 입력과 채팅 경로도 없다`는 뜻이 아니라, real parser 품질을 이번 통과 판단에 넣지 않더라도 사용자 장면이 지나갈 최소 입력과 상태 경로는 살린다는 뜻이어야 한다.

slice 목록은 진행 메모다. 비어 있어도 코딩을 막지 않고, 적혀 있어도 다음 작업 queue가 아니다. 펼친 후보가 parent feature 안의 한 필드나 한 상태를 화면까지 잇는 단계라면 slice로 충분하다. 별도 `01-01` 같은 feature spec은 독립 사용자 장면, 독립 실패 유형, 별도 상태 언어/확인 기준이 생겨 parent 진행 메모로 두면 drift될 때만 연다.

### 냄새 신호

아래 신호가 보이면 멈추고 다시 좁힌다.

- spec 항목을 다 채우기 전에는 구현을 시작할 수 없다고 느낀다.
- `이번 AC`가 제품 동작이 아니라 구현 순서표가 된다.
- Non-goals가 필요한 product path까지 닫아 버린다.
- 현재 코드 비교가 바로 파일 수정 목록이나 work-map으로 바뀐다.
- 입력 샘플, expected output, eval runner 준비만으로 product behavior를 확인했다고 말한다.
- 한 필드가 화면까지 닿기 전에 업로드, OCR, LLM, 카드 UI를 가로로 다 만들려 한다.
- 예시 파일을 현재 작업 queue나 hidden playbook처럼 따라 한다.

### 짧은 brief 예시

- 좋음: "이번 AC는 체크인 시작 시간 `근거 있음`, 늦은 도착 조건 `근거 부족`, 직접 확인 카드 경계다." — 사용자 장면 안에서 확인할 동작을 좁힌다.
- 나쁨: "체크인 feature 전체 구현, eval 추가, ingestion 개선, 카드 UI 정리, 모든 scenario 처리." — spec 전체를 작업 목록으로 바꾼다.

큰 feature를 slice로 펼치고 한 단계씩 개발하는 방법은 `tripproof-spec-driven` skill을 따른다.

완성본에 가까운 calibration sample은 아래 두 파일을 본다. 이 파일들도 현재 작업 queue가 아니라, 어떤 밀도와 경계로 spec을 남기는지 보여주는 예시다.

- [큰 feature 완성본 예시: 숙소 체크인 확인 slice](examples/example-large-feature-checkin-slice-build.md)
- [작은 독립 spec 예시: 근거 부족에서 직접 확인 카드로 올리기](examples/example-small-spec-missing-to-direct-confirm.md)
