# 2026-06-05 - 큰 feature spec과 슬라이스 빌드 모델

## 폴더 구성

- `index.md`: 결론과 현재 판단.
- `raw.md`: 이 결정에 이르며 거쳐온 고민 사례와 트레이드오프.

`raw.md`는 현재 실행 기준이 아니다. 후속 작업자는 `index.md`를 먼저 읽고, 왜 이런 결론을 했는지 필요할 때만 `raw.md`를 본다.

> 용어: 이 결정은 **feature**(spec이 다루는 기능 단위) → **slice**(feature를 짓는 빌드 단계) → **부품**(구현 조각)과, feature에서 확인할 **scenario(사례)** · **acceptance criteria(AC, 통과 조건)**를 쓴다. 외부 spec-driven 용어를 한 번 확인하고 표준어로 정렬한 결과이며, 근거는 아래 결정 6과 `raw.md`에 있다.

## 맥락

큰 feature로 spec을 잡으면 구현 덩어리가 커서 분해가 필요해 보인다. 그런데 그 분해를 어떻게 기록할지가 여러 차례 반복 논의됐다. 같은 결론에 도달하고도 기록 위치와 권한이 분명하지 않으면 다시 논의가 열렸다.

핵심 긴장은 이거다. spec-driven의 "기록하며 제어"는 살리되, 분해 기록이 product spec과 같은 권위를 가져 작업지시서나 gate가 되는 것은 막아야 한다. 이 결정은 `2026-06-03-light-spec-driven-loop`를 잇는 보강이며, 그 결정의 product-first·문서 비대화 방지 기준을 그대로 따른다.

## 결정

1. **spec은 유연하다.** 큰 feature도, 작은 보완도 spec이 된다. 미리 써서 막는 gate가 아니라 개발하며 자라는 기준이다. spec이 개발하며 *생기는* 기록(descriptive)이면 선행 gate가 될 수 없다. 이 관점 전환이 "기록"과 "gate 회피"의 충돌을 푼 지점이다.
2. **큰 feature spec 안에 slice 후보 목록을 둘 수 있다.** 단 이 목록은 진행 메모(상기용)지 통과 기준이 아니다. 비어 있어도 코딩을 막지 않고, slice가 AC를 새로 정의하지 않는다. 별도 work-map 파일은 만들지 않는다.
3. **빌드 방법과 역할 분리:** AC로 바로 좁히기 전에 구현면을 한 번 펼쳐(불확실한 PDF/OCR/LLM도 미리 Non-goals로 안 자름) 후보를 본다 → 후보를 slice로 **한 필드, 한 상태, 한 실패 유형처럼 좁혀 실데이터로 끝까지 통과**시킨다(자료 → AI → 상태 → 화면) → 나머지 부품은 stub, 부품 목업은 따로 만들지 않는다(목업 병목 차단) → 완료 기준은 컴포넌트가 아니라 화면 동작이다 → 닫은 slice는 AC 태그로 commit한다. 여기서 구현면은 넓게 펼치는 지도, slice 후보는 그 지도를 관통하는 product path 후보, 먼저 고를 slice는 이번 구현에서 화면까지 이을 build path, AC는 product behavior 관찰 기준이다. Non-goals는 기술 충실도와 확장 범위를 줄이는 장치이지, 사용자 장면을 통과시키는 최소 경로를 끊는 장치가 아니다.
4. **분리는 spec 레벨에서 일어난다.** 펼친 후보가 크고 독립적이면 별도 feature spec(`01` → `01-01`)이 될 수도 있다. 대부분은 slice로 순서대로 개발한다. slice 자체는 쪼개는 단위가 아니라 순서대로 짓는 단위다.
5. **AC home은 기존 문서다.** feature 단위 통과 기준은 이미 `docs/prd.md`(기존 product 서사 + 그룹별 AC)와 baseline 코드/test가 나눠 소유한다. feature마다 AC를 재서술하는 새 spec 파일을 자동으로 만들지 않는다.
6. **외부 용어는 한 번 확인하고 TripProof에 맞게 정렬한다.** 외부 spec-driven과 agile/XP 어휘를 확인한 결과, `feature`는 spec이 다루는 기능 단위로 가져올 만한 표준어이고, `slice`는 위계나 크기 단위가 아니라 vertical slice처럼 구현 방식에 가까운 말이다. `scenario`는 BDD 계열에서 feature 안의 구체 사례에 가깝다. 반대로 `capability` 위계, `track`, specify→plan→tasks 파이프라인, EARS, constitution/steering은 지금 TripProof에 과하다. 그래서 현재 규모의 TripProof는 무거운 정의를 들이지 않고, 운영 단위를 **feature / slice / scenario / acceptance criteria(AC)**로 정렬한다. 우리말은 표준어가 안 맞을 때만 둔다(부품, 사용자 장면, 큰/작은 작업, 확인 방법). 향후 같은 용어 조사는 이 결정을 기준으로 생략한다.

반영 위치:

- `docs/specs/README.md` — 처음 읽는 법·Light loop·문서 경계에 흡수, 용어표 정렬.
- `.claude/skills/tripproof-spec-driven/SKILL.md` — 먼저 판단할 것·권장 첫 슬라이스 감각·기록 위치·기본 경계·냄새 신호에 분산.

## 기각 또는 보류

- **분해를 별도 work-map / execution-map 파일로 두기 — 기각.** tracked 영구 파일에 번호 매긴 작업 목록을 두면 다음 구현 항목을 지시하는 queue처럼 읽힌다. `2026-06-03-light-spec-driven-loop`의 "두 현역 기준 문서가 남으면 gate/queue로 읽힌다"와 충돌한다. 분해는 spec 안 진행 메모 + 태그 commit으로 남긴다.
- **분해를 product spec 본문에 통과 기준처럼 심기 — 기각.** spec이 작업지시서가 된다. 이전 검토에서 확인한 핵심 실패다.
- **외부 방법론을 정의째 도입(capability 위계, specify→plan→tasks 파이프라인, EARS, constitution/steering) — 기각.** 현재 규모에는 과하다. 표준어 이름만 빌리고 무거운 절차는 들이지 않는다(결정 6).
- **worktree 기반 병렬 분해 장치 — 보류(deprecated).** 큰 spec을 worktree로 병렬 분해하는 무거운 장치는 현재 단계에 과하고 조기 분해를 유도한다. 유용한 핵심(구현면 펼치기·slice·stub 감각)만 이 repo의 작업 루프(`tripproof-spec-driven`)로 흡수했다.
- **feature마다 AC를 재서술하는 새 spec 파일 — 보류.** 기존 문서와 drift를 만든다. 만들 때도 기존 문서를 가리키는 thin pointer만 두고 재서술하지 않는다.

## 검증

이 모델이 과해지는지는 다음 신호로 관찰한다.

- slice 후보 목록이 통과 기준처럼 굳거나 코딩을 막기 시작한다.
- work-map / execution-map 파일이 다시 생기려 한다.
- "spec이 없어서 못 한다", "P0-A부터 순서대로" 같은 말이 나온다.
- 한 필드가 실데이터로 끝까지 돌기 전에 부품 목업을 따로 만들기 시작한다(목업 병목 신호).
- Non-goals가 실제 Gmail/PDF/OCR/LLM 같은 기술 충실도 보류가 아니라, 자료 입력·채팅·근거·카드 경계 같은 product path 자체를 닫는 말로 쓰인다.
- 구현면 펼치기 없이 slice 후보가 `seed`, `button`, `type` 같은 작은 코드 접점으로만 쪼개진다.
- AC와 slice 후보가 같은 목록처럼 합쳐진다.

## 이번 결정 밖

- 첫 slice의 실제 코드(client ↔ shared 계약 연결)는 아직 돌리지 않았다.
- LLM adapter, 실제 ingestion, eval 같은 후속 기술 후보의 도입 시점.
