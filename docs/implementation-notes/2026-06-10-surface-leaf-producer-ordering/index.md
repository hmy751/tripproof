# 2026-06-10 - Surface 이후 Leaf Producer 우선 순서

## 폴더 구성

- `index.md`: 다음 구현에서 먼저 볼 관찰과 경계.
- `raw.md`: 이 관찰의 검토 배경 재료.

`raw.md`는 현재 실행 기준이나 작업 대기열이 아니다. 현재 작업에 적용할 때는 이 `index.md`와 현재 코드 상태를 먼저 본다.

## 왜 남기나

질문 실행 기록 spec을 다루는 동안 Implementation Surface는 이미 펼쳐져 있었지만, 상위 spec 제목, 첫 AC, next slice 문장이 provider/export 쪽을 강하게 가리키면 다음 작업이 product observation contract보다 wrapper나 adapter 구현으로 기울 수 있었다.

이 노트는 구현면을 더 펼치라는 원칙을 반복하기보다, surface를 펼친 뒤 첫 구현 대상을 어떻게 고를지에 대한 ordering calibration을 남긴다.

## 관찰

상위 문서와 skill은 판단 렌즈여야 하지만, 제목, 하위 spec 번호, 첫 AC, next slice가 현재 product surface보다 강한 실행 앵커로 읽힐 수 있다.

이때 "먼저 wrapper", "no-op provider", "하위 spec 02" 같은 작업은 완료하기 쉬운 구조물로 보이지만, product path에서 실제로 생성되는 fact/record가 없으면 상위 adapter가 소비할 payload가 아직 없다.

따라서 Implementation Surface를 펼친 뒤의 다음 단계는 다시 상위 구조를 구현하는 것이 아니라, product path 안에서 실제 fact/record를 만드는 leaf producer를 고르는 쪽이어야 한다.

## 다시 볼 경계

Surface first, product leaf producer first, top-level adapter last.

첫 구현 slice는 product path 안에서 실제 event를 받아 product fact를 만드는 leaf producer여야 한다. Leaf producer first는 helper, type, schema를 먼저 만들라는 뜻이 아니다. 해당 slice는 사용자 흐름의 endpoint 또는 domain boundary에 연결되어야 하며, 어떤 product behavior를 관찰 가능하게 만드는지 한 문장으로 답할 수 있어야 한다.

Adapter, exporter, provider abstraction은 leaf producer가 만든 record를 소비할 때만 등장한다. 소비할 product payload가 없다면 no-op wrapper나 provider client는 첫 slice가 아니다.

## Calibration sample

피할 형태:

- 상위 spec이 provider/export 이름을 첫 구현 축으로 읽히게 둔다.
- next slice가 `no-op wrapper -> endpoint trace -> snapshot`처럼 adapter tree를 먼저 채운다.
- record shape 없이 trace provider 인터페이스나 logging helper를 먼저 만든다.

기준 형태:

- `/api/materials` upload event가 material id, parse status, source unit count, embedding status, failure kind 같은 product fact를 observation record로 만든다.
- `/api/questions` execution event가 material id, retrieval summary, prompt identity, answer status 같은 product fact를 record로 만든다.
- LangSmith는 이미 endpoint/domain에서 생성된 record를 export하는 sink로 붙는다.

Check:

- 이 첫 slice는 어떤 endpoint/domain에서 어떤 product fact를 생성하는가?
- 상위 adapter가 소비할 product payload가 이미 있는가?
- 문서 번호나 provider 이름을 구현 순서로 승격하고 있지 않은가?

## 어디에는 남기지 않았나

`docs/specs/README.md`에는 아직 추가하지 않았다. 구현면 펼치기 원칙은 이미 존재하므로, 이번에는 실행 순서 보정이 필요한 repo-local `spec-driven` skill과 현재 active spec에만 반영한다.

`docs/decisions/`에는 남기지 않았다. 이번 기록은 구조 채택/기각 결정이 아니라, 구현 중 반복해서 다시 볼 drift 관찰이다.

`docs/work-log.md`에는 남기지 않았다. 다음 작업 재진입 상태가 아니라, 비슷한 구현에서 다시 볼 calibration sample이다.
