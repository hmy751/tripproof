# 2026-06-23 - Layout-derived SourceUnit 보완에서 드러난 좋은 실패

## 폴더 구성

- `index.md`: 구현 중 드러난 경계 관찰과 다음에 다시 볼 기준.
- `raw.md`: 이 관찰이 생긴 배경 재료.

## 왜 남기나

Agoda 원문 PDF QA 개선 중 `pdfplumber` layout 기반 SourceUnit을 table row, table cell, line region으로 확장했다. 1차 구현은 `9f33970 feat(retrieval): PDF layout field group source unit 추가`에 고정했다.

그 뒤 `docs/engineering/` 관점으로 다시 보자, "table extraction 실패 시 line-region fallback을 추가하면 된다"는 단순 보완이 기존 SourceUnit boundary 계약을 깨뜨릴 수 있음이 테스트 실패로 드러났다. 이 실패는 우연한 red가 아니라, layout-derived SourceUnit에서 다시 봐야 할 경계를 구체적으로 보여준 사례다.

## 적용한 engineering lens

이 관찰은 `docs/engineering/`을 gate로 적용한 결과가 아니라, `docs/engineering/README.md`가 말하는 calibration reference를 코드 결과물에 다시 대 본 사례다. 특히 다음 렌즈가 실제 보완 방향을 바꿨다.

- `principle.md`의 실패·불확실성 설계: table extraction 실패는 PDF 입력에서 정상적으로 생길 수 있는 실패이므로, 전체 field group 복구 경로를 끄기보다 가능한 line-region 경로로 낮춰야 한다. 동시에 `StructuralBlock`처럼 검색과 evidence 입력으로 이어지는 중간 타입은 `lines`도 `text_override`도 없는 상태나, 파생 텍스트인데 bbox가 없는 상태를 만들 수 없게 해야 한다.
- `principle.md`의 근거 경계: 검색용 텍스트나 벡터는 원문의 파생물일 뿐 근거 자체가 아니다. table row/cell/line-region SourceUnit은 retrieval에 유리한 재구성 텍스트이므로, 어떤 원문 fragment에서 왔는지 observation metadata로 남겨야 한다.
- `testing.md`의 검증 구분: 단위 테스트는 product behavior를 대체하지 않지만, boundary 계약이 깨지는 지점은 빨리 드러낼 수 있다. 이번 좋은 실패는 production-like eval 이전에 "fallback 보강이 기존 key/value split을 침범한다"는 결정 시점의 문제를 잡았다.
- `testing.md`의 증상 추적 경계: `Remarks`, `City tax`, `special requests` 같은 문구로 boundary를 강제하면 특정 PDF 증상을 쫓는 테스트가 된다. boundary layer는 geometry와 block continuity를 neutral fixture로 검증하고, booking-domain keyword는 semantic annotation이나 recall 보조로 분리한다.
- `architecture.md`의 product/관측/eval 경계: provenance와 layout source detail은 product response body가 아니라 observation/report 경로에 남긴다. product 결과 계약을 늘리지 않고도 나중에 한 retrieval/evidence 흐름을 재구성할 수 있게 하는 쪽이 맞다.

## 관찰

첫째, table extraction 실패는 정상적인 degrade 대상이지만, table이 없다는 이유로 line-region grouping까지 꺼지면 layout 기반 복구 경로가 사라진다. 1차 구현에는 `layout.table_rows`가 비어 있으면 field group 생성을 바로 중단하는 early return이 있었다.

둘째, early return을 제거하면 line-region fallback은 살아나지만, 이미 한 줄에서 label/value가 완결된 `key_value_row`까지 큰 field group으로 다시 승격될 수 있다. 이때 기존 테스트 `test_layout_source_units_split_key_value_rows`가 깨졌고, `Arrival : 2025-03-09`, `Departure : 2025-03-13`, `Guest : ...`가 각각의 SourceUnit으로 남아야 한다는 기존 계약을 다시 확인했다.

셋째, single-line `key_value_row`를 모두 제외하면 `Remarks :`처럼 값이 뒤따르는 label-only row까지 빠진다. 필요한 구분은 "한 줄짜리 key/value"가 아니라 "separator 뒤에 실제 값이 있는 완결형 key/value"였다.

넷째, 완결형 key/value row를 group text에서 제외하더라도, 그 row가 같은 visual section 안에 끼어 있으면 section을 끊는 boundary로 쓰면 안 된다. 이 row는 source text에는 들어가지 않는 bridge로 다루되, 다음 후보와의 거리·column continuity를 판단할 때는 반영해야 했다.

다섯째, line-region group의 최소 크기를 block 개수로 판단하면 내부 block 병합 방식에 과하게 의존한다. 실제로 `Section A :` + `Alpha value`가 하나의 block으로, `Beta value` + `Gamma value`가 또 하나의 block으로 합쳐지면서 실제 4줄짜리 section이 block 2개라는 이유로 group이 생성되지 않았다. 이 기준은 block count가 아니라 line count로 보정했다.

여섯째, boundary 테스트에 Agoda/booking 문구를 직접 넣으면 layout boundary와 semantic annotation cue가 섞인다. `Remarks`, `City tax`, `special requests`를 이용해 "request group에 fee가 섞이면 안 된다"를 테스트하려 하면, 의미어를 보지 않는 boundary layer에 semantic 요구를 밀어 넣게 된다. 이 테스트는 `Section A`, `Reference ID`, `Alpha/Beta/Gamma value` 같은 neutral fixture로 바꿔 geometry와 bridge 동작만 검증하게 했다.

## 다시 볼 경계

- SourceUnit boundary 개선은 retrieval 품질 보강이지만, SourceUnit은 answer composer와 evidence grounding의 입력이기도 하다. 검색에 유리한 파생 텍스트를 만들 때는 원문 fragment provenance를 함께 남긴다.
- table extraction 실패를 degrade하더라도 기존 line/key-value boundary 계약을 침범하지 않는지 먼저 본다.
- label-only row와 complete key/value row를 같은 기준으로 다루지 않는다.
- "group에 포함하지 않음"과 "section을 끊음"은 다른 판단이다.
- layout boundary 테스트는 가능한 한 neutral fixture로 쓴다. Agoda/booking keyword는 semantic annotation이나 recall 보조 테스트에 둔다.
- 내부 block 병합 결과에 기대는 조건은 조심한다. retrieval/evidence가 소비할 source region의 크기 기준은 block count보다 line count나 bbox가 더 안정적일 수 있다.

## 어디에는 남기지 않았나

이 기록은 구조 선택을 확정하는 decision note가 아니다. 제품 동작 효과는 별도 production-like eval로 확인해야 한다.

여기에는 같은 종류의 layout-derived SourceUnit drift를 다시 볼 때 필요한 boundary calibration만 남긴다.
