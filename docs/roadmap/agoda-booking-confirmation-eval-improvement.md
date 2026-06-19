# Agoda 예약 확인서 eval 기반 기능 개선 분석

상태: 2026-06-18 수동 eval 결과와 2026-06-19 observation/report 구현 이후의 개선 지도. 확정 일정이나 완료 증명이 아니라, 다음 구현 작업을 고를 때 참고하는 문서다.

## 한 줄 결론

이번 실패는 "Agoda 문항 몇 개를 못 맞혔다"가 아니다. TripProof가 여행 자료를 **질문에 답할 수 있는 근거 단위**로 바꾸지 못한 상태에서, 큰 텍스트 덩어리 몇 개를 LLM에게 넘기고 답을 기대한 것이 핵심 문제다.

따라서 개선 방향은 특정 PDF나 특정 질문에 맞춘 예외처리가 아니다. 다음 자료가 들어와도 유지되는 방향은 아래다.

```text
자료 업로드
-> 문서 구조 정리
-> 의미 있는 근거 단위 생성
-> 질문을 필요한 하위 근거로 나눔
-> 근거 후보를 충분히 찾음
-> 답변을 조립하고 상태를 검증
-> 사용자에게 근거 있음 / 확인 필요 / 근거 부족을 정직하게 표시
```

## 이번 결과를 어떻게 봐야 하나

실행 자체는 제품 경로를 탔다.

- PDF 업로드는 성공했고 `ready`가 됐다.
- 8개 질문은 모두 제품 질문 API로 실행됐다.
- retrieval, embedding, answer composer가 모두 실행됐다.
- strict rule check는 0/8이었다.

하지만 "실행됐다"는 말은 "제품이 답할 준비가 됐다"는 뜻이 아니다. 이번 결과에서 더 중요한 신호는 다음이다.

| 관찰 | 의미 |
| --- | --- |
| PDF가 source unit 2개로만 쪼개짐 | 문서의 필드, 표, 정책, 주의사항이 검색 가능한 단위로 보존되지 않았다. |
| 질문 8개가 같은 큰 덩어리 후보를 공유 | retrieval이 질문별 근거를 고르는 역할을 거의 못 했다. |
| 체크인/체크아웃 질문에서 체크인만 답함 | 질문 안의 하위 항목을 나누지 못했다. |
| 특별 요청을 확정 조건처럼 답함 | 값과 조건/주의사항을 함께 보지 못했다. |
| 대부분 missing으로 떨어짐 | 원문에 답이 있어도 답변 조립과 grounding이 안정적으로 이어지지 않았다. |

`source unit 2개`는 대표 증상이다. 진짜 문제는 그 뒤의 전체 파이프라인이 모두 같은 약점을 공유한다는 점이다.

## 현재 자동 eval runner와 원본 PDF eval의 경계

최근 작업으로 eval runner와 HTML report는 더 쓸 만해졌다. `run.json`은 질문셋 실행 원장을 남기고, `report.html`은 product answer, observation trace, retrieval candidate, composer context, answer/evidence를 한 화면에서 보여준다. 따라서 이제는 "아무것도 안 보이니 관측부터 만들자"가 아니라, 이 report를 기준으로 실패 유형을 분류하고 다음 product 개선을 고르는 단계다.

다만 현재 기본 자동 runner를 원본 PDF 품질 eval로 착각하면 안 된다.

| 구분 | 현재 의미 |
| --- | --- |
| 2026-06-18 수동 eval | 실제 Agoda 예약 확인서 PDF와 8개 문항을 놓고 본 실패 분석의 원천이다. |
| 현재 `eval/run_question_dataset.py` 기본 실행 | 제품 API 경로와 observation/report 연결을 확인하는 integration eval이다. 기본 입력은 sample text fixture를 임시 PDF로 만든 것이다. |
| `eval/datasets/agoda-booking-confirmation/questions.json` | 원본 PDF 기준 질문셋으로 출발했지만, 현재 기본 sample fixture와 cue 문구가 항상 맞는 것은 아니다. |

즉 product code는 실제로 탄다. `/api/materials`, `/api/questions`, retrieval, answer composer, observation export를 지나간다. 하지만 기본 실행 조건은 원본 PDF 전체 품질을 재는 것이 아니라, sample fixture와 고정된 runtime config로 제품 경로와 report join을 확인하는 쪽에 가깝다.

다음 개선을 고르기 전에는 이 경계를 먼저 정리해야 한다.

- runner가 실제 PDF 파일을 material input으로 받을 수 있어야 한다.
- sample fixture run과 original PDF run을 구분해서 기록해야 한다.
- 질문셋의 cue는 `source cue`와 `answer cue`를 분리해야 한다.
- exact substring 하나로 좋은 답변을 실패 처리하지 않도록 alias나 source 기반 확인 기준을 열어야 한다.
- report의 실패 원인은 제품 실패인지, fixture/cue 불일치인지, composer backend 한계인지 구분해서 읽어야 한다.

## TripProof 기준에서 본 핵심 문제

TripProof의 제품 가치는 사용자가 넣은 여행 자료에 대해 "근거 있는 답", "확인 필요", "근거 부족"을 정직하게 나누는 것이다. 그러려면 단순히 LLM이 답을 잘 쓰는 것보다 먼저, 시스템이 원문을 잘게 되찾을 수 있어야 한다.

현재 흐름은 대략 이렇다.

```text
PDF text
-> page 안에서 길이 기준 chunk
-> source unit 몇 개
-> 질문 하나로 top-k retrieval
-> LLM이 JSON 답변 생성
-> snippet이 원문에 있으면 supported 가능
```

이 구조는 빠르게 시작하기에는 좋지만, 여행 예약 문서 QA에는 약하다.

- 문서의 의미 단위가 아니라 글자 수 단위로 쪼갠다.
- 질문이 여러 항목을 묻는지 알지 못한다.
- retrieval 후보가 넓어서 LLM이 직접 문서 안을 다시 뒤져야 한다.
- evidence snippet이 원문에 포함되는지만으로는 답변의 조건까지 검증되지 않는다.
- supported / needs_review / missing 판단을 LLM 응답에 너무 많이 맡긴다.

## 왜 "Agoda 전용 필드 읽기"가 답이 아닌가

이전 개선안처럼 "Agoda 예약 확인서에서 자주 나오는 필드를 먼저 읽자"는 표현은 위험하다. 그렇게 만들면 다음 자료가 Booking.com, Airbnb, 항공권, 투어 바우처, 렌터카 영수증으로 바뀌는 순간 다시 막힌다.

Agoda 문항셋은 구현 대상이 아니라 **실패를 재현하는 대표 fixture**여야 한다. 구현은 특정 업체명이 아니라 여행 문서에서 반복되는 정보 구조를 다뤄야 한다.

좋은 방향:

- 라벨-값 구조를 찾는다. 예: `Arrival: ...`, `Room Type: ...`
- 정책/주의사항 문단을 찾는다. 예: 취소, 노쇼, 추가 비용, 특별 요청
- 한 값과 그 값을 제한하는 조건을 함께 묶는다.
- 문서마다 표현이 달라도 근거 단위와 상태 판단 방식은 재사용한다.

나쁜 방향:

- `NonSmoke`, `LargeBed` 문자열만 보면 확인 필요로 바꾼다.
- `Agoda` PDF 전용 파서를 만든다.
- eval 질문 문구에 맞춰 답변을 직접 만든다.
- supported를 늘리려고 grounding 검사를 느슨하게 한다.

## 개선해야 할 6개 층

### 1. 문서 입력 품질

현재 PDF 텍스트는 사람이 보는 문서 구조를 많이 잃는다. 줄바꿈, 중복 단어, 표 구조 손실 때문에 `Arrival`, `Departure`, `Room Type`, 취소 정책 같은 정보가 하나의 긴 흐름에 섞인다.

개선 목표는 OCR 도입 자체가 아니다. 먼저 현재 추출 텍스트를 질문 가능한 형태로 정리해야 한다.

해야 할 일:

- 추출 텍스트의 줄, 라벨, 값, 문단 경계를 보존한다.
- 중복 단어와 불필요한 줄바꿈을 줄인다.
- 원문 위치로 돌아갈 수 있는 offset 또는 locator를 유지한다.
- 파싱 결과에 대한 품질 지표를 남긴다. 예: 글자 수, 줄 수, 감지된 라벨 수, 생성된 source unit 수

### 2. 의미 있는 source unit 생성

현재 source unit은 page 안에서 길이 기준으로 잘린다. 이번 PDF처럼 1-2페이지짜리 예약 확인서는 source unit이 2개 정도만 생긴다. 이러면 검색이 "정확한 근거 찾기"가 아니라 "페이지 덩어리 찾기"가 된다.

source unit은 LLM에게 넣기 좋은 chunk가 아니라, 사용자가 나중에 근거로 다시 확인할 수 있는 원문 단위여야 한다.

개선 방향:

- 글자 수 기준 chunk를 fallback으로 내리고, 구조 기반 source unit을 먼저 만든다.
- 라벨-값 row, 정책 문단, 주의사항 문단, 비용 안내, 특별 요청 안내를 별도 단위로 만든다.
- 너무 작은 단위가 문맥을 잃지 않도록 주변 heading이나 관련 caveat를 함께 보존한다.
- 각 source unit에 `kind` 같은 metadata를 붙인다. 예: field, policy, warning, fee, request, contact

예시:

```text
SourceUnit A: Arrival / 체크인 날짜
SourceUnit B: Departure / 체크아웃 날짜
SourceUnit C: Room Type / Number of Rooms / Adults / Children
SourceUnit D: Cancellation / No-show policy
SourceUnit E: Remarks + special request caveat
SourceUnit F: City tax / on-site extra cost notice
```

이건 Agoda 전용 구조가 아니다. 여행 문서에서 흔히 보이는 정보 유형이다.

### 3. 질문 분해

사용자 질문은 하나처럼 보여도 실제로는 여러 답을 요구할 수 있다.

예:

- "체크인하고 체크아웃하는 날짜가 언제야?" → 체크인 날짜 + 체크아웃 날짜
- "예약된 객실과 인원은 어떻게 돼?" → 객실 타입 + 객실 수 + 성인 수 + 아동 수
- "취소하거나 노쇼하면 어떻게 돼?" → 무료 취소 기준 + 임박 취소 조건 + 노쇼 조건

현재 구조는 질문 하나로 retrieval을 한 번 실행하고, LLM이 알아서 여러 항목을 만들기를 기대한다. 이러면 반쪽 답변이 나와도 시스템이 알아차리기 어렵다.

개선 방향:

- 질문을 먼저 하위 정보 요청으로 나눈다.
- 하위 요청별로 근거 후보를 찾는다.
- 답변도 하위 항목별 item으로 만든다.
- 일부만 찾았으면 전체를 supported로 보지 않는다. 찾은 항목은 supported, 못 찾은 항목은 missing으로 분리한다.

### 4. retrieval recall과 후보 검증

이번 run에서 retrieval은 실행됐지만, retrieval이 잘했다는 뜻은 아니다. 후보가 2개뿐이면 모든 질문이 사실상 같은 후보를 보게 된다. 이 상태에서는 vector search 점수나 top-k가 제품 품질을 크게 설명하지 못한다.

개선 방향:

- 질문별로 기대되는 근거 유형이 후보에 들어왔는지 관찰한다.
- source unit 수, 평균 길이, 후보 다양성, 후보가 포함한 metadata를 run artifact에 남긴다.
- 하나의 질문에 여러 하위 요청이 있으면 하위 요청별 retrieval 결과를 따로 본다.
- vector search만 믿지 말고 라벨/키워드 기반 lexical recall을 함께 쓴다.

중요한 점: lexical rule은 답변을 만드는 하드코딩이 아니라, 후보를 놓치지 않기 위한 recall 장치로 써야 한다.

### 5. 답변 조립

LLM을 빼자는 뜻이 아니다. LLM의 역할을 바꿔야 한다.

지금은 LLM이 넓은 source unit을 읽고 답변, 상태, 근거 snippet을 거의 한 번에 만든다.

개선 후에는 시스템이 먼저 근거 후보를 좁히고, LLM은 그 후보를 바탕으로 사용자에게 읽기 좋은 답변을 조립한다.

```text
현재:
질문 -> 큰 source unit 몇 개 -> LLM이 답변/상태/근거를 한 번에 결정

개선:
질문 -> 하위 요청 -> 근거 후보 -> 항목별 answer draft -> 상태 검증 -> LLM은 표현 정리
```

이렇게 해야 다음 자료에서도 일관성이 생긴다. LLM은 "문서 전체를 뒤지는 사람"이 아니라 "찾아온 근거를 설명하는 사람"에 가까워져야 한다.

### 6. 상태와 근거 검증

현재 grounding은 evidence snippet이 source unit text 안에 있는지를 본다. 이 방어선은 필요하지만 충분하지 않다.

추가로 봐야 하는 것:

- 질문이 요구한 하위 항목이 모두 답변됐는가.
- 근거가 값만 보여주는가, 조건까지 보여주는가.
- 값 근처에 "요청", "가능", "상황에 따라", "별도 지불", "취소 시" 같은 제한 문맥이 있는가.
- supported라고 하려면 근거가 사용자의 행동에 충분한가.
- 불충분하면 missing이 아니라 needs_review가 맞는 경우는 아닌가.

이 검증도 특정 문구 하드코딩으로 닫으면 안 된다. 처음에는 사용자의 행동을 크게 바꾸는 여행 정보부터 일반 규칙으로 잡는다.

오답 비용이 큰 여행 정보:

- 특별 요청 / 선호 조건
- 취소 / 환불 / 노쇼
- 현장 추가 비용
- 체크인 가능 시간과 날짜
- 체크인 시 필요한 준비물과 현장 확인 항목

## 우선순위 재정렬

### 0단계: 원본 PDF 기준 eval baseline 정리

최근 observation/report 구현으로 기본 관측 뼈대는 생겼다. 이제 첫 단계는 관측을 더 쌓는 것이 아니라, 자동 eval이 무엇을 보고 있는지 믿을 수 있게 정리하는 것이다.

개선 확인 신호:

- runner가 실제 Agoda PDF 파일을 입력으로 받을 수 있다.
- sample fixture run과 original PDF run이 `run.json`에서 구분된다.
- `questions.json`의 cue가 원문 근거 확인용 cue와 답변 표현 확인용 cue로 분리된다.
- exact substring 실패가 곧 제품 실패로 오해되지 않는다.
- `report.html`에서 실패 질문을 열었을 때 fixture/cue 문제인지 product path 문제인지 구분할 수 있다.

이 단계의 목표는 점수를 올리는 것이 아니다. 같은 8문항을 다시 돌렸을 때 "실패가 어디서 생겼는지"를 믿고 읽을 수 있게 만드는 것이다.

### 1단계: 현재 report로 실패 유형을 분류한다

이미 생긴 HTML report는 다음 작업을 고르는 입구다. 실패 질문을 열고, `Eval verdict`와 `Evidence path`를 같이 보면서 원인을 아래처럼 나눈다.

| 실패 유형 | 의미 | 다음 조치 |
| --- | --- | --- |
| 입력/eval 기준 문제 | 원본 PDF가 아니라 sample fixture를 봤거나, cue 기준이 맞지 않는다 | runner 입력과 질문셋 기준을 정리한다 |
| source unit 문제 | 원문은 있지만 너무 큰 덩어리라 후보 선택이 흐릿하다 | source unit 구조화를 먼저 한다 |
| retrieval 문제 | source unit은 있는데 질문별 후보에 들어오지 않는다 | 하위 요청별 retrieval과 lexical recall을 본다 |
| answer composer 문제 | 후보는 있는데 답변 item/evidence로 조립되지 않는다 | 답변 조립과 prompt를 본다 |
| 상태 검증 문제 | 답은 나왔지만 supported/needs_review/missing이 틀렸다 | 상태 검증을 강화한다 |

관측을 더 추가한다면 이 분류에 필요한 것만 붙인다. 예를 들면 source unit count, 평균/최대 길이, kind 분포, 질문별 candidate kind, missing reason 정도다. observation을 별도 1급 기능처럼 키우지는 않는다.

### 2단계: source unit을 구조 기반으로 바꾼다

첫 구현 목표는 점수를 올리는 것이 아니라, 문서가 QA 가능한 단위로 들어오게 만드는 것이다.

개선 확인 신호:

- 같은 PDF에서 source unit이 2개가 아니라 필드/문단 단위로 늘어난다.
- 체크인/체크아웃, 객실/인원, 취소/노쇼, 추가 비용, 특별 요청이 서로 다른 근거 단위로 잡힌다.
- 각 단위는 원문 snippet으로 돌아갈 수 있다.
- 기존 fixed-size chunking은 fallback으로 유지한다.

### 3단계: 질문을 하위 요청으로 나눈다

개선 확인 신호:

- 체크인/체크아웃 질문은 최소 2개 항목으로 답한다.
- 객실/인원 질문은 객실 타입, 객실 수, 성인, 아동을 분리한다.
- 취소/노쇼 질문은 조건을 나눠 답한다.
- 일부만 찾았을 때 전체를 supported로 뭉개지 않는다.

### 4단계: retrieval을 하위 요청별로 실행한다

개선 확인 신호:

- 각 하위 요청마다 관련 source unit 후보가 들어온다.
- 후보가 없으면 answer composer로 넘기기 전에 missing 이유를 알 수 있다.
- 큰 source unit 하나가 모든 질문을 대표하지 않는다.

### 5단계: 상태 검증을 강화한다

개선 확인 신호:

- 값만 있고 조건이 없으면 supported로 확정하지 않는다.
- 특별 요청, 추가 비용, 취소 정책은 조건 문맥까지 근거로 잡는다.
- 위험한 오답 supported를 먼저 없앤다.

### 6단계: LLM prompt를 그 다음에 고친다

prompt 수정은 필요하지만 첫 번째 처방이 아니다. 입력 단위와 retrieval 후보가 나쁜 상태에서 prompt만 고치면 다음 자료에서 다시 무너진다.

prompt는 아래가 준비된 뒤 고친다.

- source unit이 의미 단위로 들어온다.
- 질문이 하위 요청으로 나뉜다.
- composer가 항목별 후보를 받는다.
- 상태 검증이 supported를 방어한다.

## 팀 구성

3명으로 시작할 수 있다.

| 역할 | 맡을 일 |
| --- | --- |
| 문서 이해 / Retrieval 엔지니어 | 파싱 품질, source unit 구조화, retrieval recall 개선 |
| AI / Answer 엔지니어 | 질문 분해, 답변 조립, 상태 검증, LLM prompt 정리 |
| Eval / Product QA | 실패 유형 분류, run artifact 보강, before/after 비교 |

5명으로 넓히면 이렇게 나눈다.

| 역할 | 맡을 일 |
| --- | --- |
| Parsing 엔지니어 | PDF 텍스트 정리, 라벨-값/문단 경계 감지 |
| Retrieval 엔지니어 | source unit metadata, hybrid retrieval, rerank |
| LLM 엔지니어 | question decomposition, answer composer, JSON 안정화 |
| Backend 엔지니어 | API 응답, observation, run artifact, 저장 구조 |
| Product/Eval 담당 | 여행자 행동 기준, 오답 비용 우선순위, regression 질문셋 관리 |

## 이번 문항셋을 어떻게 써야 하나

이번 8문항은 제품 구현을 하드코딩하기 위한 목록이 아니다. 아래를 확인하는 regression set으로 써야 한다.

| 문항 유형 | 확인하려는 능력 |
| --- | --- |
| 체크인 준비물 | 필수 행동 안내를 근거와 함께 찾는가 |
| 체크인/체크아웃 날짜 | 한 질문 안의 여러 필드를 모두 답하는가 |
| 체크인 시작 시간 | 문서에 없는 시간을 추정하지 않는가 |
| 숙소 이름/위치 | 라벨-값 필드를 안정적으로 읽는가 |
| 객실/인원 | 묶음 필드를 분리해 답하는가 |
| 취소/노쇼 | 조건형 정책을 나눠 설명하는가 |
| 현장 추가 비용 | 가능성/조건을 단정하지 않는가 |
| 특별 요청 | 요청과 확정을 구분하는가 |

목표는 바로 8/8이 아니다. 순서는 이렇다.

1. 위험한 supported를 없앤다.
2. source unit이 문서 의미 단위로 만들어지는지 확인한다.
3. retrieval 후보에 기대 근거가 들어오는지 확인한다.
4. 여러 필드 질문이 완전하게 답되는지 확인한다.
5. strict rule check를 올린다.

## 하지 말아야 할 것

- Agoda 전용 파서로 닫지 않는다.
- 질문별 답변을 직접 하드코딩하지 않는다.
- 특정 문자열만 보고 상태를 바꾸지 않는다.
- prompt만 고쳐서 해결하려고 하지 않는다.
- source unit이 큰 덩어리인 상태에서 rerank나 모델만 바꾸지 않는다.
- supported를 늘리려고 evidence 검사를 약하게 만들지 않는다.
- eval 점수를 제품 기능처럼 취급하지 않는다.

## 다음 작업 제안

다음 작업은 바로 "특별 요청 오답 차단"이나 "prompt 수정"이 아니다. 먼저 **원본 PDF 기준으로 믿을 수 있는 eval baseline을 만들고, 그 report를 기준으로 source unit 구조화를 시작하는 것**이다.

첫 slice:

```text
원본 PDF를 runner 입력으로 받기
-> sample fixture run과 original PDF run 구분
-> source cue / answer cue 기준 정리
-> 현재 report로 baseline 실패 유형 분류
-> 구조 기반 source unit 생성
-> 같은 8문항을 원본 PDF 기준으로 재실행
```

이 slice가 끝나면 점수가 바로 크게 오르지 않아도 된다. 대신 아래 질문에 답할 수 있어야 한다.

1. 이번 run은 sample fixture 기준인가, original PDF 기준인가.
2. 실패는 eval cue 불일치인가, product path 실패인가.
3. PDF가 몇 개의 의미 단위로 나뉘었는가.
4. 각 질문이 필요한 근거 후보를 retrieval에서 받았는가.
5. missing은 원문 부재 때문인가, retrieval 실패 때문인가, composer/grounding 실패 때문인가.
6. 틀린 supported가 구조적으로 줄어들 가능성이 생겼는가.

그 다음에 질문 분해와 답변 조립을 붙인다. 이 순서가 TripProof 제품에 맞다.
