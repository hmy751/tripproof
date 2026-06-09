# Specs

현재 specs 운영 기준은 이 README다. spec-driven 구조를 light loop로 낮춘 배경 결정은 `docs/decisions/2026-06-03-light-spec-driven-loop/`를 본다.

`docs/specs/`에는 여러 작업으로 이어지는 제품 동작 기준만 둔다. 과거의 `00-spec-driven-development.md`는 `docs/archive/spec-driven/00-spec-driven-development.md`에 보관된 스냅샷이며, 현재 작업 queue나 절차 gate가 아니다.

작은 수정마다 spec을 만들 필요는 없다. 나중에 다시 봐야 할 목표, 제약, 결정, 남은 쟁점만 짧게 남긴다.

## 처음 읽는 법

TripProof의 light spec-driven은 큰 작업에서 사용자 장면, 경계, 확인 기준을 짧게 맞춰 사람과 AI가 같은 완료 조건을 보게 하는 작업 루프다.

spec은 승인 gate나 작업 목록이 아니라, 큰 작업에서 무엇을 통과로 볼지와 무엇을 Non-goals로 둘지를 맞추는 얇은 기준이다. 미리 써서 막는 gate가 아니라 개발하며 자라는 기준이다. 큰 feature는 여러 작업으로 이어질 제품 동작 기준이 필요할 때 feature spec으로 열고, 작은 보완도 독립 실패 유형이나 제품 경계가 있으면 작은 spec으로 열 수 있다. 다만 작은 수정마다 spec을 만드는 것은 아니다. 아래 순서는 읽는 렌즈이지 필수 실행 순서가 아니며, 처음 읽을 때는 이렇게 본다.

1. **사용자 장면**: 사용자가 어떤 자료를 넣고 무엇을 물어보는가.
2. **Goal**: 이 feature가 끝났다고 말할 사용자-visible 결과는 무엇인가.
3. **Rules**: 그 결과를 만들 때 AI, 화면, 상태가 넘지 말아야 할 경계는 무엇인가.
4. **Non-goals**: 중요하지 않아서가 아니라, 이 feature를 작게 유지하기 위해 의도적으로 빼는 것은 무엇인가.
5. **상태 언어**: 사용자가 화면에서 보게 될 말. 내부 타입명은 그 뒤에 본다.
6. **구현면 펼치기**: 큰 feature라면 자료 입력, AI 후보, 정규화, 채팅, 근거, 카드, 대시보드, guard 같은 큰 면을 먼저 펼친다.
7. **Slice 후보**: 펼친 구현면을 얇게 관통하는 product path 후보를 본다.
8. **먼저 고를 slice**: 이번 구현에서 실제로 화면까지 이을 경로 하나를 고른다.
9. **이번 AC / 확인 방법**: 선택한 경로가 어떤 product behavior를 관찰하게 하는지 확인한다.

큰 feature는 6-8을 기본으로 거쳐 구현면을 펼치고 slice 후보를 고른다. 이미 경로가 좁은 작은 spec이나 bugfix라면 6-8을 생략할 수 있고, 생략할 때는 왜 생략하는지 한 줄만 남긴다.

스펙을 구현하기 전에는 현재 스펙이 단독 기준인지, 상위 feature spec이나 앞뒤 하위 스펙처럼 함께 읽어야 할 참조 맥락이 있는지 먼저 확인한다. 참조 맥락이 있으면 부모 스펙의 사용자 장면, 먼저 고를 slice, 이번 AC와 인접 스펙의 입력/출력 계약을 짧게 본다. 목적은 관련 문서를 작업 목록으로 만드는 것이 아니라, 현재 스펙이 product path 안에서 받는 입력과 넘기는 출력을 놓치지 않는 것이다. 입력이 앞 단계 product artifact가 아니라 fixture/seed로 바뀌거나, 출력이 뒤 단계 계약이 아니라 화면 통과용 고정값이 되면 구현을 더 좁히기 전에 다시 확인한다.

용어는 이렇게 쓴다. 표준 spec-driven 용어를 쓰고, 맞는 표준어가 없을 때만 우리말을 둔다.

| 용어 | 뜻 |
| --- | --- |
| feature | spec이 다루는 기능 단위. 크기는 고정하지 않으며, 한 사용자 장면을 끝까지 통과시키는 단위가 기본이다. 예: 숙소 체크인 확인 |
| 구현면 | feature를 화면까지 통과시키는 데 관련되는 큰 구현 면. 예: 자료 입력/ingest, AI 후보, 정규화, 채팅, 인라인 근거, 카드 초안, 대시보드 출처, guard |
| slice | 펼친 구현면을 얇게 관통하는 빌드 경로. 보통 한 필드, 한 상태, 한 실패 유형으로 좁혀 `자료 -> extractor/AI 후보 -> 상태 -> 화면`까지 닿게 한다. 작은 TODO나 부품 완성표가 아니다 |
| stub | 선택한 slice가 지나갈 수 있게 임시로 받치는 구현. 이번에 깊게 판단하지 않는 면을 줄이는 장치이지, 사용자 장면의 최소 경로를 닫는 핑계가 아니다 |
| 부품 | feature를 이루는 구현 조각. 부품은 slice 안에서 필요할 때만 만들고, 부품 목록 자체를 통과 기준으로 삼지 않는다 |
| scenario (사례) | feature에서 확인할 구체 상황. 나중에 AC를 확인할 때 꺼내는 대표 사례지 작업 순서표가 아니다 |
| acceptance criteria (AC) | feature의 통과 조건 또는 product proof 관찰 기준. slice와 연결되지만 같은 목록은 아니다 |
| user scene (사용자 장면) | 사용자가 실제로 처한 상황, 입력 자료, 질문 |
| check method (확인 방법) | 테스트, 수동 확인, 화면 관찰처럼 완료를 확인하는 방법 |

작업 크기는 따로 가른다: 실패했을 때 원인과 판단이 흐려질 만한 **큰 작업**이면 아래 brief를 남기고, **작은 작업**이면 바로 진행한다.

## 문서 경계

spec에는 현재 repo에서 확인 가능한 목표, 제약, 결정, 열린 질문, 검증 후보만 남긴다.

feature 단위 통과 기준(AC)은 새 spec이 자동으로 다시 쓰지 않는다. 이미 `docs/prd.md`와 baseline 코드/test가 나눠 소유한 기준이 있으면, 새 spec은 그 기준을 재서술하기보다 필요한 만큼 가리킨다.

아직 없는 product flow, eval run, before/after, metric, public case study를 완료된 proof처럼 쓰지 않는다. repo 밖 개인 자료, 공고/포트폴리오 맥락, 대화 원문, 도구 이름도 product 근거처럼 남기지 않는다.

TripProof의 기본 방향은 product-first다. eval은 product behavior를 호출하고 관찰한다. product code가 eval sample, run artifact, metric output에 의존하게 만들지 않는다.

지금 만들지 않을 문서 예시:

- 실제 run 없는 eval 결과표
- metric threshold 확정 문서
- 증거 없는 public before/after case study
- 작업량 메타를 product proof처럼 보이게 하는 운영 로그

## Light spec-driven loop

TripProof의 spec-driven은 문서 gate가 아니라 큰 작업을 작게 잡기 위한 작업 루프다.

큰 작업이면 작업 시작 전에 5-6줄 정도의 brief를 둔다. 큰 feature라면 구현면과 slice 후보를 본 뒤 `먼저 고를 slice`를 같이 적는다.

```text
왜 지금:
사용자 장면:
먼저 고를 slice:
제품 흐름(필요할 때만): 입력 -> 변환 -> 출력 / 넘지 말 선
이번 AC:
주의할 점:
남은 판단:
```

큰 작업의 기준은 실패했을 때 원인과 판단이 흐려지는가다. 사용자 flow가 바뀌거나, AI 위임 범위가 크거나, AC가 애매하거나, 실패 유형 분해가 필요하거나, 다음 세션이 이어받아야 하면 큰 작업으로 본다.

작은 작업은 별도 spec 없이 바로 진행한다. 오타, 좁은 UI 조정, 기존 AC 안의 bugfix, 작은 refactor, 테스트 보강은 commit, PR, test output 근처에 남기는 것으로 충분하다.

`이번 AC`는 기본 1-3개로 제한한다. 숫자보다 한 사용자 장면이나 한 실패 유형으로 관찰 가능한지를 먼저 본다. spec은 작업을 만들지 않고, 이미 선택한 사용자 장면을 좁히는 데만 쓴다. 큰 feature에서는 AC로 바로 뛰기 전에 구현면을 펼치고, slice 후보를 본 뒤, 먼저 고를 slice를 하나 정한다. slice 후보 목록은 진행 메모지 통과 기준이나 다음 작업 queue가 아니다. 비어 있어도 코딩을 막지 않고, 별도 work-map 파일은 만들지 않는다.

새 spec 파일은 여러 세션으로 이어지는 제품 동작 기준이 필요하거나, AC drift가 반복되거나, 검토 과정에서 정리된 사용자-facing 실패 유형이나 제품 기준이 다음 작업에서도 유지되어야 하거나, 사용자-facing 실패 유형을 분리해야 할 때만 만든다.

### Spec이 보존해야 할 판단

spec은 빈칸을 채우는 문서 양식이 아니라, 다음 작업자가 사용자 장면과 경계, 확인 기준을 다시 잡을 수 있게 하는 calibration sample이다. 아래 항목은 필요할 때 붙잡는 판단 질문이지, 모든 spec에 같은 순서와 같은 밀도로 들어가야 하는 템플릿이 아니다.

- **사용자 장면**: 기능명이 아니라 사용자가 어떤 자료를 넣고 어떤 판단을 하려는 순간인지 쓴다. 좋은 예는 "예약 확인서와 호스트 안내를 넣고 체크인 시간과 늦은 도착 조건을 묻는다"이고, 나쁜 예는 "숙소 정보 추출 기능"처럼 구현명만 남기는 것이다.
- **Goal**: 끝났다고 말할 사용자-visible 결과를 좁힌다. 좋은 예는 "체크인 시작 시간은 근거와 함께 답하고, 늦은 도착 조건이 없으면 `근거 부족`으로 멈춘다"이다. 나쁜 예는 "숙소 체크인 AI를 완성한다"처럼 완료 기준이 커지는 것이다.
- **Rules**: Goal을 만들 때 AI/화면/상태가 넘지 말아야 할 경계를 둔다. 좋은 예는 "자료 밖 일반 지식으로 답을 보충하지 않는다"이다. 나쁜 예는 "가능하면 친절하고 자세하게 답한다"처럼 안전 경계가 취향 문구로 흐르는 것이다.
- **Non-goals**: 덜 중요해서 버리는 목록이 아니라, 이번 feature나 slice의 통과 판단에서 제외한 범위다. "모르는 것"과 "이번에 하지 않는 것"을 같은 말로 두지 않는다.
- **상태 언어**: 사용자가 화면에서 보는 말을 먼저 둔다. 내부 타입명은 그 뒤에 매핑한다. `근거 부족` 답변도 사람이 값을 채워 올리면 `직접 확인` 카드가 될 수 있다는 식으로 상태 축과 결정 축을 섞지 않는다.
- **구현면 펼치기**: 큰 feature에서는 먼저 큰 면을 펼친다. 자료 입력, AI 후보, 정규화, 채팅, 근거, 카드, 대시보드, guard처럼 사용자 장면이 지나갈 면을 본다. 이 단계는 작업표가 아니라 빠뜨린 면과 과하게 잘린 면을 확인하는 지도다.
- **Slice 후보**: slice 후보는 구현면을 얇게 관통하는 product path다. 예를 들어 "체크인 시작 시간 답변"은 자료 입력, 근거를 제출하는 extractor, 정규화, 채팅, 인라인 근거를 지난다. 실제 Gmail/PDF/OCR ingestion처럼 이번에 깊게 다루지 않는 면은 stub으로 받을 수 있다.
- **먼저 고를 slice**: 후보 중 이번 구현에서 실제로 화면까지 이을 하나를 고른다. 다른 후보는 Non-goals가 아니라 다음 slice 후보로 남는다. 후보가 독립 사용자 장면, 독립 실패 유형, 별도 상태 언어를 갖게 되면 sub-spec으로 승격할 수 있다.
- **이번 AC**: 전체 feature가 아니라 이번 작업에서 관찰할 1-3개 product behavior다. AC는 product proof의 관찰 기준이고, slice는 그 AC 일부를 화면까지 잇는 build path다. 둘은 연결되지만 같은 목록이 아니다.
- **확인 방법**: 완료 여부는 문서가 아니라 제품 동작으로 확인한다. 좋은 확인은 화면에서 상태 문구, 근거, 카드 승격 경계를 보는 것이고, 나쁜 확인은 spec 항목이 모두 채워졌는지만 보는 것이다.

### Non-goals / 구현면 / slice

Non-goals는 선택한 사용자 장면을 통과시키는 데 필요한 경로를 끊는 장치가 아니다. 줄이는 대상은 보통 기술 충실도와 확장 범위다. 실제 PDF/OCR parser, full provider 품질, 모든 필드, eval dashboard는 이번 slice 밖으로 둘 수 있지만, 자료 입력, 근거를 제출하는 후보 생성 계약, 상태 판정, 화면 표시처럼 사용자 장면이 지나갈 최소 경로는 살아 있어야 한다.

LLM 불확실성은 데모로 대체하지 않는다. 줄일 수 있는 것은 provider 품질, ingestion 충실도, 처리 범위이지, `자료 -> 후보/evidence -> 상태 -> 화면`으로 이어지는 product causality가 아니다. 여기서 product causality는 자료가 바뀌면 답도 바뀌고, evidence quote가 없으면 `근거 있음`이 될 수 없는 인과다. deterministic baseline이나 stub은 같은 계약을 통과시키는 test double일 수 있지만, product proof의 주인공이 되면 안 된다.

허용되는 축소는 사용자 입력 material을 읽고 evidence quote 계약을 통과하는 deterministic adapter처럼 같은 인과를 얇게 통과시키는 것이다. 금지되는 축소는 고정 seed나 hard-coded answer를 화면에 보여 주고 product proof라고 부르는 것이다.

구현면 펼치기는 제외할 것을 찾는 절차가 아니다. 큰 feature에서 `ingest`, `chat`, `AI 후보`, `정규화`, `근거`, `카드`, `대시보드`, `guard` 같은 면을 먼저 펼치고, 현재 코드와 비교해 이미 되는 것과 stub으로 둘 것을 본다. 그 다음에야 slice 후보를 고른다.

slice 목록은 진행 메모다. 비어 있어도 코딩을 막지 않고, 적혀 있어도 다음 작업 queue가 아니다. 펼친 후보가 parent feature 안의 한 필드나 한 상태를 화면까지 잇는 단계라면 slice로 충분하다. 별도 `01-01` 같은 feature spec은 독립 사용자 장면, 독립 실패 유형, 별도 상태 언어/확인 기준이 생겨 parent 진행 메모로 두면 drift될 때만 연다.

### 냄새 신호

아래 신호가 보이면 멈추고 다시 좁힌다.

- spec 항목을 다 채우기 전에는 구현을 시작할 수 없다고 느낀다.
- `이번 AC`가 제품 동작이 아니라 구현 순서표가 된다.
- Non-goals가 필요한 product path까지 닫아 버린다.
- 구현면 펼치기 없이 slice 후보가 바로 작은 코드 TODO로 쪼개진다.
- `ingest`, `chat`, `card`, `dashboard` 같은 큰 면이 사라지고 `seed`, `button`, `type` 같은 작은 접점만 남는다.
- AC와 slice가 같은 목록처럼 합쳐진다.
- stub이 slice를 통과시키는 임시 구조가 아니라 안 해도 되는 이유처럼 쓰인다.
- LLM hallucination이나 PDF/OCR 복잡도를 이유로 `seed -> hard-coded answer -> 화면`만 만들고 product proof라고 부른다.
- deterministic adapter가 grounded extractor 계약의 test double이 아니라, 실제 후보 생성 경로를 대신하는 완성 기능처럼 쓰인다.
- `real LLM은 뒤로 둔다`가 provider 품질 보류가 아니라 AI 후보/evidence 계약 자체를 닫는 말로 쓰인다.
- raw/debug/API 응답을 사용자가 읽는 결과로 변환하지 않고 product slice가 닫혔다고 말한다.
- 현재 코드 비교가 바로 파일 수정 목록이나 work-map으로 바뀐다.
- 입력 샘플, expected output, eval runner 준비만으로 product behavior를 확인했다고 말한다.
- 한 필드가 화면까지 닿기 전에 업로드, OCR, LLM, 카드 UI를 가로로 다 만들려 한다.
- 예시 파일을 현재 작업 queue나 hidden playbook처럼 따라 한다.

### 짧은 brief 예시

- 좋음: "이번 AC는 체크인 시작 시간 `근거 있음`, 늦은 도착 조건 `근거 부족`, 직접 확인 카드 경계다." — 사용자 장면 안에서 확인할 동작을 좁힌다.
- 나쁨: "체크인 feature 전체 구현, eval 추가, ingestion 개선, 카드 UI 정리, 모든 scenario 처리." — spec 전체를 작업 목록으로 바꾼다.

`spec-driven` skill은 brief 작성 여부, 즉시 구현 여부, 확인 지점을 판단할 때 참고하는 runtime 기준이다. 이 README와 아래 예시는 매번 읽는 gate가 아니라, scope 축소나 product path 판단이 흔들릴 때 감각을 보정하는 calibration reference다.

완성본에 가까운 calibration sample은 아래 두 파일을 본다. 이 파일들도 현재 작업 queue가 아니라, 어떤 밀도와 경계로 spec을 남기는지 보여주는 예시다.

- [큰 feature 완성본 예시: 숙소 체크인 확인 slice](examples/example-large-feature-checkin-slice-build.md)
- [작은 독립 spec 예시: 근거 부족에서 직접 확인 카드로 올리기](examples/example-small-spec-missing-to-direct-confirm.md)
