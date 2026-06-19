# Source unit structure improvement

작성일: 2026-06-19

상태: draft sub-spec. 원문 PDF baseline에서 확인한 실패를 줄이기 위한 첫 product 개선 slice다.

이 문서의 중심은 runner나 report 필드를 늘리는 것이 아니다. 원문 PDF가 retrieval과 answer evidence로 쓰일 수 있는 source unit으로 더 잘 들어오게 만드는 것이다.

## 사용자 장면

개발자가 원문 Agoda PDF와 8개 질문셋을 돌린다. baseline report에서 필요한 정보가 큰 page-like 덩어리에 묻히거나, 질문에 필요한 조건 문맥이 candidate로 잘 올라오지 않는 것을 확인한다.

그 다음 source unit 생성 방식을 개선하고, 같은 원문 PDF와 같은 질문셋, 같은 production-like runtime 조건으로 다시 실행한다. before/after report에서 source unit kind, locator, retrieval candidate, answer/evidence가 어떻게 달라졌는지 확인한다.

Before 기준 artifact:

- `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/`
- `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/report.html`
- `eval/runs/question-dataset/agoda-original-pdf-baseline-20260619-production/run.json`

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

## PDF extractor 선정

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

구현 방향:

- `PdfLayoutExtractor` 경계를 두고 기본 구현을 `PdfPlumberLayoutExtractor`로 둔다.
- extractor 출력은 page, bbox, text, line/word order, font/spacing, table-like row 단서를 가진 layout record여야 한다.
- source unit boundary는 page, bbox, y-gap, x alignment, font/spacing 변화, row/list/table-like 반복 같은 물리 단서를 우선 사용한다.
- 체크인, 취소, 도시세, 특별 요청 같은 도메인 단어는 source unit을 직접 만드는 hard boundary가 아니라, 이미 생성된 구조 단위의 recall/annotation을 보조하는 약한 신호로만 쓴다.
- layout record가 충분하지 않을 때만 기존 text chunking fallback을 사용하고, 그 경우 report에서 fallback 경로임을 확인할 수 있어야 한다.

## 개선 기준

원문 PDF는 page-length 덩어리 몇 개로만 남으면 안 된다. 아래처럼 여행 예약 문서에서 반복되는 의미 단위가 source unit으로 드러나야 한다.

- 체크인 준비물, 예약 확정서, 신분증, 결제 카드처럼 사용자가 현장에서 해야 할 일
- 체크인/체크아웃, 객실, 인원처럼 라벨과 값이 붙어 있는 정보
- 취소, 노쇼, 환불, 현장 결제처럼 조건이 중요한 정책 문단
- 추가 비용, 세금, 보증금, 숙소에서 확인해야 하는 비용 안내
- 특별 요청, 주의사항, 숙소 확인 필요 항목

source unit은 최소한 사람이 report에서 위치와 유형을 추적할 수 있어야 한다.

- `locator`: page, block, row 등 원문 위치를 다시 찾을 수 있는 정보
- `kind`: label-value, policy, warning, fee, request note 같은 정보 유형
- `char_length`: 너무 큰 덩어리인지 확인하기 위한 길이 단서

정확한 field name과 kind 목록은 구현 시 현재 자료 모델에 맞춰 정한다. 이 문서는 값 목록을 고정하는 것이 아니라, source unit이 질문 가능한 의미 단위가 되어야 한다는 제품 기준을 고정한다.

현재 before baseline의 직접 관찰은 다음과 같다.

- 원문 PDF는 `source_unit_count=2`로만 생성됐다.
- 두 source unit이 전 질문의 retrieval candidate로 반복해서 올라온다.
- 필요한 단서가 candidate context 안에 있어도 answer composer가 일부만 뽑거나 evidence state를 오판한다.

따라서 이 slice의 첫 성공 신호는 답변 문구 개선이 아니라, 질문별 required cue가 더 좁은 source unit과 locator로 추적되는 것이다.

## 구현 규칙

- Agoda 전용 parser를 만들지 않는다.
- 특정 질문 문구를 보고 답을 만드는 rule을 넣지 않는다.
- lexical rule은 생성된 layout/source unit의 annotation이나 후보 recall 보조로 사용할 수 있지만, source unit boundary나 product answer를 직접 만들면 안 된다.
- 값과 조건 문맥을 분리해서 위험한 supported 상태를 만들지 않는다.
- source unit의 granularity를 줄이더라도 원문 locator와 evidence snippet을 잃지 않는다.
- product response body에는 observation/debug/eval field를 추가하지 않는다.

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
5. product response body에 observation/debug/eval field가 추가되지 않았는지 확인한다.

## 이번 slice에서 섞지 않는 범위

- 질문 분해 전체를 이 slice에 넣지 않는다. 이후 `03-question-decomposition.md`에서 다룬다.
- 하위 요청별 retrieval 전체 개편을 이 slice에 넣지 않는다. 이후 `04-subrequest-retrieval.md`에서 다룬다.
- 상태 검증 전체 개편을 이 slice에 넣지 않는다. 이후 `05-state-validation-answer-assembly.md`에서 다룬다.
- source unit 구조화가 되기 전에 prompt 수정만으로 점수를 올리려 하지 않는다.
- eval 점수 threshold나 release gate를 확정하지 않는다.
