# Source unit structure improvement

작성일: 2026-06-19

상태: 완료. V1(`9b09b59`), field-group follow-up(`9f33970`, `e29480f`), 2026-06-24의 glyph/line-region cleanup까지 반영한 뒤 최종 production-like 재측정을 `09-20260624T072332Z-field-groups-cleaned-after-production`으로 완료했다. 이 문서는 02 source unit boundary slice의 기준 기록으로 닫고, 남은 QA 실패는 `03`~`05`에서 질문 분해, 하위 요청별 retrieval, 상태 검증/답변 조립 문제로 이어서 다룬다.

이 문서의 중심은 runner나 report 필드를 늘리는 것이 아니다. 원문 PDF가 retrieval과 answer evidence로 쓰일 수 있는 source unit으로 더 잘 들어오게 만드는 것이다.

## 사용자 장면

개발자가 원문 Agoda PDF와 8개 질문셋을 돌린다. baseline report에서 필요한 정보가 큰 page-like 덩어리에 묻히거나, 질문에 필요한 조건 문맥이 candidate로 잘 올라오지 않는 것을 확인한다(시작 baseline 관찰의 권위 서술은 `01-original-pdf-observation-baseline.md`에 둔다).

그 다음 source unit 생성 방식을 개선하고, 같은 원문 PDF와 같은 질문셋, 같은 production-like runtime 조건으로 다시 실행한다. before/after report에서 source unit kind, locator, retrieval candidate, answer/evidence가 어떻게 달라졌는지 확인한다.

이 slice의 측정은 한 번이 아니라 이어진 timeline이다. 아래 run은 같은 입력·같은 8문항을 같은 production-like runtime으로 돌렸고, 역할이 다르다.

| 시점 | run | 역할 |
| --- | --- | --- |
| Before (2026-06-19) | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/` | layout 개선 전 시작점. source unit 구조 문제를 드러낸 근거 |
| After v1 (2026-06-19) | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/` | layout 기반 source unit 구조화의 직접 효과 측정 |
| Current (2026-06-23) | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/06-20260623T092247Z-postreconcile-current-baseline-production/` | reconciliation 이후 같은 조건 재측정. 현재 기준 baseline |
| Field-group final (2026-06-24) | `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/09-20260624T072332Z-field-groups-cleaned-after-production/` | field-group/glyph/line-region cleanup 후 02 최종 확인 run |

before/after report 위치:

- Before report: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/report.html`
- Before run JSON: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/01-20260619T083605Z-before-baseline-production/run.json`
- After v1 report: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/report.html`
- After v1 run JSON: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/05-20260619T123416Z-layout-v1-after-production/run.json`
- Field-group final report: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/09-20260624T072332Z-field-groups-cleaned-after-production/report.html`
- Field-group final source units: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/09-20260624T072332Z-field-groups-cleaned-after-production/source-units.md`

After v1 구현 commit: `9b09b59 feat(materials): PDF 레이아웃 기반 source unit 구조화`

## Product 흐름

```text
원문 PDF
-> pdfplumber layout extraction
-> source unit 생성
-> retrieval candidate
-> answer/evidence
-> 사용자에게 보이는 QA 결과
```

이번 slice는 `source unit 생성`을 개선한다. eval runner, report, `run.json`은 개선 효과를 보기 위한 소비자다.

## V1 구현 결과

`9b09b59`에서 다음을 구현했다.

- `pdfplumber`를 기본 PDF layout extraction 경로로 추가했다. `pypdf` plain text extraction은 fallback으로 유지한다.
- `ParsedPdf.layout_pages`와 내부 layout model(`PageLayout`, `PdfLine`, `PdfWord`)을 추가했다.
- `build_source_units(..., layout_pages=...)`가 layout이 있으면 structural segmentation을 사용하고, layout이 없거나 실패하면 기존 fixed-size text chunking으로 fallback한다.
- SourceUnit `metadata` JSON에 `extraction_backend`, `structural_kind`, `kind`, `bbox`, `line_count`, `page`, `fallback_used`를 저장한다.
- observation/report의 retrieval candidate와 composer context에 source unit metadata를 표시한다. product response body는 바꾸지 않는다.

V1/current 비교에 쓰인 세 run의 runtime config는 같다: `retrieval_backend=supabase`, `embedding_provider=ollama`(`embedding_model=nomic-embed-text-v2-moe`, `embedding_dimensions=768`, `embedding_auto_generate=true`), `answer_composer=ollama`(`answer_model=gemma3:4b`), `retrieval_top_k=3`, `retrieval_similarity_threshold=0.0`, `mode=production`. 같은 config라야 시점 간 차이를 구현·substrate 변화로 읽을 수 있다.

source unit 구조화의 효과를 timeline으로 보면 다음과 같다.

| 지표 | Before (06-19) | After v1 (06-19) | Current (06-23) |
| --- | --- | --- | --- |
| `source_unit_count` | 2 | 40 | 40 |
| unique retrieval candidate source units | 2 | 9 | 9 |
| rule pass | 0/8 | 0/8 | 0/8 |
| evidence state match | 2/8 | 4/8 | 3/8 |

- source unit count는 layout v1에서 `2 -> 40`으로 늘었다. 이 layout chunking은 결정적이라, reconciliation 이후 current에서도 `40`으로 그대로 유지된다.
- evidence state match는 큰 page-like source unit 두 개에 모든 질문이 기대던 문제를 줄였다는 신호다(`2/8 -> 4/8`). 다만 answer correctness가 통과됐다는 뜻은 아니다(V1/current 비교의 세 시점에서 rule pass는 모두 `0/8`).
- current(06-23) state match는 `3/8`(`checkin_action`, `missing_checkin_start_time`, `room_and_party`)으로, after v1의 `4/8`보다 한 항목 적다(이번에는 `cancellation_policy`가 미일치).
- 이 `4/8 -> 3/8` 차이는 구조화 후퇴가 아니다. after v1과 current의 retrieval candidate는 8문항 모두 질문별로 동일했다(같은 source unit index·순위, 같은 `score`/`lexical_score`/`vector_score`, unique candidate `9`로 동일). `cancellation_policy`(`AGODA-P0-06`)도 retrieval 입력은 같고, 같은 context를 받은 `gemma3:4b` answer composer 출력만 `supported -> missing`으로 갈렸다. 즉 관찰상 retrieval substrate(Supabase 단일·`lexical_ranking`)는 이 차이를 만들지 않았고, 달라진 것은 단일 run answer 출력뿐이다. `lexical_ranking`/Supabase 단일은 06-19와 06-23 사이의 코드 구조 변화이긴 하나 관찰된 retrieval 출력에는 영향이 없었다. 단일 run answer 비결정성으로 보는 것은 아직 가설이며, 02의 완료 여부와 별도로 다룬다.

조건 문맥 항목의 실패가 current에서도 유지되므로, 이 slice 뒤의 작업(`03`~`05`)은 여전히 유효하다.

자세한 after-run 해석, PDF screenshot/bbox 비교, 평가 기준은 `docs/work-log.md`의 `2026-06-19 - Agoda 원문 PDF source unit v1 구현 후 관찰` 항목에 기록되어 있다. reconciliation 이후 재측정 기록은 같은 work-log의 `2026-06-23 - reconciliation 이후 Agoda 원문 PDF baseline 재측정` 항목에 기록되어 있다. 관련 work-log의 2026-06-23 재측정 기록도 이 문서의 관찰과 같은 기준으로 해석한다: retrieval 출력은 동일했고, 차이는 composer 출력에서 발생했다.

## Field-group follow-up 구현/측정 결과

`9f33970 feat(retrieval): PDF layout field group source unit 추가`에서 V1 위에 다음을 추가했다.

- `PageLayout`에 `pdfplumber` table row/cell extraction 결과를 담는 `PdfTableRow`, `PdfTableCell`을 추가했다.
- `build_source_units(layout_pages=...)`가 line block뿐 아니라 table row, table cell, uncovered line region을 field group SourceUnit 후보로 만들 수 있게 했다.
- SourceUnit metadata에 `layout_source`, `table_index`, `row_index`, `column_index`, `cell_count`, `group_block_count`를 observation/report 경로로 노출했다.
- `Arrival/Departure`, room/party, remarks 계열처럼 라벨·값·보조 라벨이 한 질문에서 함께 retrieval될 수 있는 구조 단위를 만들기 시작했다.

`e29480f fix(retrieval): layout field group 경계 보강`은 `docs/engineering/`의 provenance, degrade, invariant 기준을 반영해 다음을 추가했다.

- table extraction이 실패하거나 table row가 없더라도 line-region field group을 시도한다. table failure가 전체 field group 복구 경로를 끄지 않게 하는 degrade 보강이다.
- `StructuralBlock`이 빈 block이나 bbox 없는 layout-derived region을 만들지 못하게 invariant를 추가했다.
- layout-derived SourceUnit이 검색과 evidence grounding 입력으로 이어지는 점을 고려해 `source_text_role`, `source_fragment_count`, 내부 `source_fragments`를 metadata에 남긴다. 이 provenance는 observation/report 경로에만 노출하고 product response body는 바꾸지 않는다.
- complete key/value row는 line-region group text에 포함하지 않되, 같은 visual section 안에 끼어 있으면 bridge로 사용해 section continuity를 끊지 않는다.
- line-region 최소 크기 판단을 내부 block count가 아니라 실제 line count 기준으로 보정했다.
- text-only dedupe가 서로 다른 위치의 같은 문구를 지우지 않도록 bbox overlap을 함께 본다.
- boundary 회귀 테스트는 Agoda/booking keyword에 기대지 않는 neutral geometry fixture로 보강했다. booking-domain keyword는 boundary 생성이 아니라 semantic annotation/recall 보조 쪽으로 분리한다.

2026-06-24 cleanup에서는 `07`/`08` source unit 관찰에서 드러난 두 가지 문제를 더 보완했다.

- pdfplumber가 일부 Hangul/CJK 글자를 겹쳐 추출해 `대대한한민민국국`처럼 보이던 artifact를 word/table text 수집 단계에서 정리한다. ASCII 영문/숫자 반복은 보존한다.
- large/value-only table cell이 주변 line-region field group을 과하게 억제하지 않게 했다. 반대로 compact labeled table row/cell은 중복 source unit을 만들지 않도록 line-region을 억제한다.
- 넓은 줄 묶음이 값과 조건 문맥을 담는 경우는 보존하고, 상단 좌우 컬럼의 라벨만 억지로 한 줄에 붙은 cross-column label cluster는 버린다.
- `Property/Address`, `Remarks + special request`처럼 line-region이 실제 질문 단위로 유용한 곳은 남기되, `Booking ID ... Number of Rooms ... Booking Reference No ...`처럼 서로 다른 컬럼 라벨이 우연히 이어진 묶음은 제거한다.

검증:

- `npm run check`에서 server/client/test 묶음이 통과했다(80 passed, 1 warning).
- 최종 production-like run은 `09-20260624T072332Z-field-groups-cleaned-after-production`이다.
- runtime config는 current baseline(`06`)과 같다: `retrieval_backend=supabase`, `embedding_provider=ollama`(`nomic-embed-text-v2-moe`, 768), `answer_composer=ollama`(`gemma3:4b`), `top_k=3`, `similarity_threshold=0.0`, `mode=production`.

최종 run 관찰:

- `source_unit_count=52`.
- rule pass는 `1/8`, evidence state match는 `6/8`이다. rule pass는 literal cue coverage 중심이므로 02의 성공/실패를 단독 판정하지 않는다.
- state match가 true인 항목은 `checkin_action`, `stay_dates`, `missing_checkin_start_time`, `property_location`, `room_and_party`, `on_site_extra_costs`다.
- `property_location`은 `u.10` line-region field group에서 `Property/Address` 라벨과 실제 값이 함께 잡혀 supported evidence로 복구됐다.
- `Remarks + NonSmoke/LargeBed + 특별 요청은 숙소 상황에 따라 결정`은 `u.12` line-region field group으로 보존됐다. 다만 `special_request_boundary`의 최종 state는 여전히 false라서, 이후에는 source unit boundary보다 subrequest retrieval/state validation 쪽에서 다룬다.
- `08`에서 보이던 중복 glyph artifact는 `09` source-units 문서에서 `대대한`, `체체`, `福福`, `하하카`, `예예약`, `모모든` 패턴이 사라진 것으로 확인했다.
- `08`에 있던 과도한 `Booking ID ... Number of Rooms ... Booking Reference No ... Number of Extra Beds ...` line-region은 `09`에서 제거됐다.

따라서 `07`/`08`은 field-group 방향성 관찰로, `09`는 02 source unit boundary slice의 최종 확인 run으로 본다.

구현 중 드러난 경계 관찰은 `docs/implementation-notes/2026-06-23-layout-source-unit-good-failures/`에 별도로 기록했다. 이 note는 layout-derived SourceUnit에서 같은 boundary drift를 다시 볼 때 참고하는 calibration material이다.

## PDF extractor 선정 (follow-up 판단 포함)

이번 slice의 기본 PDF extractor는 `pdfplumber`로 지정한다. 목표는 Agoda 전용 문구 parser를 만드는 것이 아니라, PDF의 물리 구조를 먼저 관찰 가능한 record로 바꾸고 그 위에서 source unit을 나누는 것이다.

`pdfplumber`를 먼저 쓰는 이유:

- 현재 문제는 plain text 추출 자체보다, 원문 PDF 안의 블록, 라벨-값 행, 표/목록 유사 구조, 작은 안내 문단의 경계를 잃는 것이다.
- `pdfplumber`는 character, line, rectangle, page object, table extraction, visual debugging을 제공하므로 source unit locator와 layout-first segmentation에 필요한 primitive를 얻기 쉽다.
- 예약 확인서 계열 PDF는 우선 scanned image가 아니라 machine-generated PDF를 대상으로 보며, 이 범위에서는 OCR보다 layout extraction의 품질이 제품 실패를 더 직접적으로 좌우한다.
- 라이선스는 MIT라 제품 기본 dependency로 두기 쉽다. 반면 `PyMuPDF`는 빠르고 layout API가 강하지만 AGPL/commercial license 선택이 필요하므로 기본값이 아니라 별도 결정 후 optional backend로만 검토한다.
- 기존 `pypdf` 기반 plain text 추출은 layout extraction 실패, 암호화/비정상 PDF, 최소 smoke용 fallback으로 남긴다.

감수하는 tradeoff:

- `pdfplumber`/`pdfminer.six` 계열은 `PyMuPDF`보다 느릴 수 있다. 현재 ingestion/eval 규모에서는 라이선스 안정성과 구조 관찰 가능성을 우선한다.
- image-only scan, 낮은 품질의 OCR PDF, 복잡한 multi-column/table layout은 이 선택만으로 해결되지 않는다. 이런 입력은 extraction quality를 낮게 표시하거나 이후 OCR/backend 확장 대상으로 분리한다.
- table extraction 결과를 그대로 정답 구조로 믿지 않는다. source unit 생성은 항상 page, bbox, raw text, 인접 line/row context를 함께 보존해야 한다.
- `pdfplumber`가 제공하는 것은 layout 관찰값이지 의미 판정이 아니다. `kind`나 semantic hint는 구조 단위가 만들어진 뒤 붙이는 annotation이어야 한다.

열린 구현 방향:

- 이번 02 slice는 `pdf.py`의 module-level 함수 경로(`_parse_pdf_with_pdfplumber`)와 `chunking.py`의 `build_source_units(layout_pages=...)`로 닫는다. 다음에 PDF backend나 추출 품질을 더 키우게 되면 `PdfLayoutExtractor` 경계를 두고 기본 구현을 `PdfPlumberLayoutExtractor`로 분리하는 방향(추출 backend 추상화)을 검토한다. 이는 이번 slice의 남은 작업이 아니라 별도 구조화 방향이다.
- extractor 출력은 page, bbox, text, line/word order, font/spacing, table-like row/cell 단서를 가진 layout record여야 한다.
- source unit boundary는 page, bbox, y-gap, x alignment, font/spacing 변화, row/list/table-like 반복 같은 물리 단서를 우선 사용한다. 이번 slice에서는 table row/cell과 line-region을 적용하고 `09` production-like run으로 과도하게 넓거나 좁은 region을 한 차례 보정했다.
- 체크인, 취소, 도시세, 특별 요청 같은 도메인 단어는 source unit을 직접 만드는 hard boundary가 아니라, 이미 생성된 구조 단위의 recall/annotation을 보조하는 약한 신호로만 쓴다.
- layout record가 충분하지 않을 때만 기존 text chunking fallback을 사용하고, 그 경우 report에서 fallback 경로임을 확인할 수 있어야 한다.

## 개선 기준 (follow-up)

원문 PDF는 page-length 덩어리 몇 개로만 남으면 안 된다. 아래처럼 여행 예약 문서에서 반복되는 의미 단위가 source unit으로 드러나야 한다.

- 체크인 준비물, 예약 확정서, 신분증, 결제 카드처럼 사용자가 현장에서 해야 할 일
- 체크인/체크아웃, 객실, 인원처럼 라벨과 값이 붙어 있는 정보
- 취소, 노쇼, 환불, 현장 결제처럼 조건이 중요한 정책 문단
- 추가 비용, 세금, 보증금, 숙소에서 확인해야 하는 비용 안내
- 특별 요청, 주의사항, 숙소 확인 필요 항목

source unit은 최소한 사람이 report에서 위치와 유형을 추적할 수 있어야 한다.

- 저장해야 하는 것 — `locator`: page, block, row 등 원문 위치를 다시 찾을 수 있는 정보 / `kind`: label-value, policy, warning, fee, request note 같은 정보 유형.
- report에서 보이면 되는 것 — `char_length`: 너무 큰 덩어리인지 확인하기 위한 길이 단서. 이미 observation/report에서 `len(source_unit.text)`로 파생되므로 metadata에 따로 저장할 필요는 없다.

정확한 field name과 kind 목록은 구현 시 현재 자료 모델에 맞춰 정한다. 이 문서는 값 목록을 고정하는 것이 아니라, source unit이 질문 가능한 의미 단위가 되어야 한다는 제품 기준을 고정한다.

before baseline의 직접 관찰(권위 서술은 `01`)이 말하는 것은 두 page-length 덩어리로는 질문별 required cue를 분리해 추적할 수 없다는 점이다. 따라서 이 slice의 첫 성공 신호는 답변 문구 개선이 아니라, 질문별 required cue가 더 좁은 source unit과 locator로 추적되는 것이다.

V1과 field-group final에서 확인된 직접 관찰은 다음과 같다.

- SourceUnit은 40개로 늘었고, 이 run에서 관측된 structural kind는 `key_value_row`, `paragraph`, `heading_paragraph`, semantic kind는 `label_value`, `policy`, `fee`, `request_note`, `general`이 report에 표시된다. 코드가 생성할 수 있는 kind는 이보다 넓다(structural에 `list_item`, `text_chunk`, semantic에 `warning`도 있으나 이 run에서는 관측되지 않았다).
- V1만 놓고 실제 PDF screenshot과 bbox overlay를 비교하면, 구현은 아직 cell/row-first가 아니라 text-line-first segmentation에 가까웠다.
- field-group follow-up은 이 관찰에서 출발해 `rect/table/cell region -> row/field group -> source unit -> semantic annotation` 방향을 코드에 반영했다.
- `09` 기준 SourceUnit은 52개이며, `Property/Address`, `Remarks + special request`는 line-region field group으로 재구성된다. 반대로 상단 예약 정보와 객실 수 컬럼이 우연히 한 줄로 붙던 cross-column label cluster는 제거됐다.
- 남은 실패는 source unit이 전혀 없어서라기보다, 가져온 후보를 질문 하위 요청별로 나누고 조건 문맥과 함께 검증하는 쪽에 가깝다.

## 구현 규칙

- Agoda 전용 parser를 만들지 않는다.
- 특정 질문 문구를 보고 답을 만드는 rule을 넣지 않는다.
- lexical rule은 생성된 layout/source unit의 annotation이나 후보 recall 보조로 사용할 수 있지만, source unit boundary나 product answer를 직접 만들면 안 된다.
- 값과 조건 문맥을 분리해서 위험한 supported 상태를 만들지 않는다.
- source unit의 granularity를 줄이더라도 원문 locator와 evidence snippet을 잃지 않는다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.
- layout-derived SourceUnit을 만들 때는 검색용 재구성 텍스트가 어떤 원문 fragment에서 왔는지 observation/report metadata로 추적 가능해야 한다.

## Acceptance Criteria

1. 원문 PDF에서 생성된 source unit은 page-length 덩어리만이 아니라 라벨-값, 정책/주의사항, 비용, 특별 요청 안내 같은 의미 단위를 포함한다.
2. 각 source unit은 locator와 kind를 가져 report에서 원문 근거 위치와 정보 유형을 확인할 수 있다.
3. 같은 8문항을 다시 실행했을 때 report의 `Evidence path`에서 질문별 retrieval candidate가 어떤 source unit을 탔는지 before/after로 비교할 수 있다.
4. 특별 요청, 취소/노쇼, 현장 추가 비용처럼 조건 문맥이 중요한 항목은 값만 보고 supported로 단정하지 않는다.
5. 개선은 sample fixture가 아니라 원문 PDF baseline과 같은 입력으로 확인한다.
6. before/after 비교는 가능한 한 같은 production-like runtime으로 실행한다. deterministic fake embedding, memory-only retrieval, `missing` composer로 만든 run은 구조 smoke로만 보고 원문 PDF QA 개선 근거로 승격하지 않는다.

## 확인 방법

1. `01-original-pdf-observation-baseline.md` 기준으로 production-like before baseline을 만든다.
2. source unit 생성 경로를 개선한다.
3. 같은 원문 PDF와 같은 `questions.json`, 같은 runtime 조건으로 다시 실행한다.
4. before/after report에서 source unit count, kind 분포, candidate locator, answer/evidence 변화를 비교한다.
5. 시점 간 수치를 비교할 때는 각 run의 runtime config(backend/embedding/top_k/threshold/composer)가 같은지 먼저 확인하고, 차이가 있으면 그 차이를 전제로만 해석한다.
6. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 질문 분해 전체를 이 slice에 넣지 않는다. 이후 `03-question-decomposition.md`에서 다룬다.
- 하위 요청별 retrieval 전체 개편을 이 slice에 넣지 않는다. 이후 `04-subrequest-retrieval.md`에서 다룬다.
- 상태 검증 전체 개편을 이 slice에 넣지 않는다. 이후 `05-state-validation-answer-assembly.md`에서 다룬다.
- source unit 구조화가 되기 전에 prompt 수정만으로 점수를 올리려 하지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.

## 후속 확인 항목

(A) 02 field-group follow-up 측정 — 완료:

1. `09-20260624T072332Z-field-groups-cleaned-after-production`에서 같은 원문 PDF, 같은 8문항, 같은 production-like runtime으로 확인했다.
2. `Property/Address`와 `Remarks + special request boundary`는 line-region field group으로 보존된다. `Arrival/Departure`, 객실/인원 계열은 table row/cell source unit으로 유지된다.
3. 새 metadata(`layout_source`, `source_text_role`, `source_fragment_count`, table/row/column index, bbox)는 observation/report 경로에서 확인된다. product response body는 바꾸지 않았다.
4. 과도하게 넓던 cross-column line-region과 중복 glyph artifact는 제거했다.

(B) eval 해석과 가설 검증 — 02 밖으로 분리:

5. eval 해석에서는 `rule pass`, `state_matched`, `required_evidence_cues`, `must_not_claim`, report-only metric label을 분리해서 본다. 현재 자동 pass는 semantic judge가 아니라 literal cue coverage 중심이다.
6. current(06-23)에서 `cancellation_policy`가 다시 미일치로 돌아간 것은 retrieval 입력이 같은 채 composer 출력만 갈린 사례다. 이것이 단일 run answer 비결정성의 범위인지 가르려면, 같은 config로 같은 8문항을 여러 번 돌려 state match의 흔들림 폭을 확인한다. 다만 이 문제는 source unit boundary 완료 여부와 섞지 않는다.

(C) 03~05로 넘기는 것 — 다음 작업:

7. 질문 분해(`03`), 하위 요청별 retrieval(`04`), 상태 검증/답변 조립(`05`)은 각 문서가 담당한다.
8. 02를 다시 여는 경우는 새 PDF backend, OCR, extractor abstraction처럼 source unit extraction 자체의 범위를 새로 정의할 때다. 현재 Agoda 원문 PDF QA 개선 흐름에서는 02를 완료로 본다.
