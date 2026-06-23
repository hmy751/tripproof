# Raw Notes - Layout-derived SourceUnit 보완에서 드러난 좋은 실패

이 파일은 `index.md` 관찰의 배경 재료다.

## 왜 raw가 필요한가

이번 관찰은 코드가 한 번에 올바른 방향으로 정리된 사례가 아니라, 보완을 시도하면서 테스트 실패가 차례로 드러난 사례다. 나중에 이 장면을 다시 보려면 "무엇이 깨졌고, 그 실패가 어떤 판단을 바꿨는지"가 남아 있어야 한다.

## 기준점

- 기준 커밋: `9f33970 feat(retrieval): PDF layout field group source unit 추가`
- 직전 문서 기준 커밋: `f4e419c docs(harness): engineering reference 운영 기준 정리`
- 보완 관찰은 `9f33970` 이후 변경 검토 과정에서 정리했다.
- 관련 파일:
  - `apps/server/retrieval/chunking.py`
  - `apps/server/tests/test_retrieval_chunking.py`
  - `apps/server/questions/observation.py`
  - `eval/html_report.py`

## engineering lens와 코드 위치

이번 재검토에서 실제로 코드 판단을 바꾼 `docs/engineering` 렌즈는 다음과 같다.

- `principle.md`의 "단 일부 실패가 정상인 자리는 멈추지 말고 한 단계 낮춘다": `pdfplumber` table extraction 실패는 전체 PDF parse 실패가 아니므로, table row/cell이 없더라도 line-region grouping은 시도할 수 있어야 했다.
- `principle.md`의 "잘못된 상태는 가능하면 타입으로 못 만들게 둔다": `StructuralBlock`은 line 기반 block과 layout-derived region block을 모두 담게 되면서 빈 block이나 bbox 없는 derived block을 만들 수 있었다. 보완은 `__post_init__` invariant로 이 상태를 막았다.
- `principle.md`의 "검색용 텍스트나 벡터는 원문의 파생물일 뿐, 그 자체가 근거가 아니다": table row/cell/line-region SourceUnit은 검색과 composer 입력으로 쓰이므로, `source_text_role`, `source_fragment_count`, `source_fragments`를 observation metadata로 남겨 파생 텍스트의 provenance를 추적하게 했다.
- `testing.md`의 "테스트가 특정 우회를 콕 집어 막는 식으로 늘어나면 증상을 쫓는 중": `City tax`나 `special requests`를 boundary negative test에 직접 넣으면 geometry layer와 semantic layer가 섞인다. 그래서 boundary test는 neutral fixture로 바꾸고, domain keyword는 semantic annotation 쪽에 둔다.
- `architecture.md`의 "관측은 내부 record가 먼저, 외부 export는 그걸 소비하는 sink": 새 metadata는 `source_unit_metadata_detail`과 `eval/html_report.py` report 경로로만 드러냈고, product response body 계약에는 추가하지 않았다.

## 실패 흐름

### 1. table 없는 line-region fallback을 켜자 기존 key/value split이 깨짐

1차 구현은 `layout.table_rows`가 없으면 `_page_field_group_blocks`가 바로 빈 배열을 반환했다. 이를 제거하자 table이 없는 PDF에서도 line-region grouping이 가능해졌다.

그러나 기존 `test_layout_source_units_split_key_value_rows`가 깨졌다. 기대는 다음 세 SourceUnit이었다.

```text
Arrival : 2025-03-09
Departure : 2025-03-13
Guest : MYEONGYEON HAM
```

실제로는 세 줄이 하나의 field group으로 묶였다.

```text
Arrival : 2025-03-09
Departure : 2025-03-13
Guest : MYEONGYEON HAM
```

이 실패가 보여준 경계는 "fallback을 켜는 것"과 "기존 완결 key/value row를 다시 grouping하는 것"이 다르다는 점이다.

### 2. single-line key/value를 모두 제외하자 label-only row까지 빠짐

처음 보정은 `key_value_row`이고 line count가 1이면 line-region 후보에서 제외하는 것이었다. 이 보정은 완결형 key/value를 보호했지만, `Remarks :`처럼 separator 뒤 값이 비어 있고 다음 줄이 실제 값인 label-only row까지 제외했다.

필요한 조건은 "한 줄"이 아니라 "separator 뒤에 값이 있는가"였다.

```text
완결형: Arrival : 2025-03-09
label-only: Remarks :
```

이후 `_is_complete_single_line_key_value_block`은 separator 뒤에 non-empty text가 있을 때만 true가 되도록 바뀌었다.

### 3. complete key/value bridge를 skip하자 section continuity가 끊김

완결형 key/value row를 field group text에 넣지 않는 것은 맞지만, 같은 visual column 안에 끼어 있는 경우 그 row 때문에 section을 flush하면 뒤따르는 continuation을 잃는다.

관찰한 구조는 다음과 같다.

```text
Section A :
Alpha value
Reference ID : ABC-123
Beta value
Gamma value
```

여기서 `Reference ID : ABC-123`은 group text에 들어가면 안 되지만, `Beta value`, `Gamma value`가 같은 section에 이어지는지 판단할 때는 bridge 역할을 한다. 그래서 skipped bridge를 별도로 들고 있다가 다음 candidate의 gap/column 판단에 사용했다.

### 4. block count 기준은 내부 병합 방식에 흔들림

neutral fixture로 바꾼 뒤 line-region group이 생성되지 않는 실패가 다시 나왔다. 실제 줄은 네 줄 이상이었지만, 내부 block 생성 결과는 두 block이었다.

```text
block 1:
Section A :
Alpha value

block 2:
Beta value
Gamma value
```

기존 기준은 `len(blocks) < 3`이면 group을 만들지 않는 방식이었다. 이 기준은 retrieval/evidence가 소비할 region 크기가 아니라 내부 block 병합 결과를 보고 있었다. 보정 후 기준은 `sum(block.line_count for block in blocks) < 3`으로 바뀌었다.

### 5. Agoda 문구 negative test는 boundary와 semantic cue를 섞었다

처음에는 다음과 같은 실제 Agoda/booking에 가까운 fixture로 request group과 fee/guest 혼합을 확인하려 했다.

```text
Remarks :
NonSmoke,LargeBed
City tax may be paid on site.
Guest list : Example Guest
All special requests are subject to property availability.
```

이 fixture는 실제 실패 장면을 잘 닮았지만, boundary layer가 의미어를 보지 않는다는 원칙과 충돌했다. `City tax`를 request group에서 빼려면 geometry만으로 충분한지, semantic cue가 필요한지를 먼저 구분해야 한다.

그래서 boundary 테스트는 neutral fixture로 바꾸었다.

```text
Section A :
Alpha value
Reference ID : ABC-123
Beta value
Gamma value
```

이 테스트는 다음만 본다.

- label-only row와 value line이 line-region group을 만든다.
- complete key/value bridge는 group text에 들어가지 않는다.
- bridge는 section continuity를 끊지 않는다.
- table로 이미 덮인 header 영역은 line-region group에 섞이지 않는다.

Agoda/booking keyword는 boundary가 아니라 semantic annotation이나 retrieval recall 보조 테스트로 다루는 것이 맞다.

## 확인된 결과

보완 후 관련 단위 테스트는 통과했다.

```text
uv run pytest apps/server/tests/test_retrieval_chunking.py -q
10 passed
```

전체 검증도 통과했다.

```text
npm run check
74 passed, 1 warning
```

## 다시 찾기 위한 키워드

이 note는 비슷한 PDF layout SourceUnit 작업에서 같은 boundary 신호를 다시 보기 위한 기록이다.

특히 다음 표현을 검색하면 이 장면을 찾을 수 있다.

- layout-derived SourceUnit
- 좋은 실패
- table 없는 line-region fallback
- complete key/value bridge
- label-only row
- neutral geometry fixture
- block count vs line count
