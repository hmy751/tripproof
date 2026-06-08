# 숙소 체크인 02 - Source unit과 RAG index boundary

상태: sub-spec draft.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

PDF 본문을 긴 문자열 하나로 AI나 extractor에 넘기면, 나중에 답변과 fact가 실제 원문 어디에서 왔는지 추적하기 어렵다. 이번 단계는 01에서 파싱한 PDF 본문을 locator가 있는 source unit으로 나누고, RAG 검색에 쓸 수 있는 index record boundary를 잡는 데까지 닫는다.

이 단계는 답을 찾거나 근거를 확정하는 단계가 아니다. `SourceUnit`은 원문이고, `IndexRecord`와 embedding/vector는 그 원문을 다시 찾기 위한 파생물이다. Retrieval candidate, accepted evidence, `TripFact`, `EvidenceState` 판단은 03에서 다룬다.

## 사용자 장면

사용자는 Agoda 예약 확정 PDF를 넣고 전체 자료함에 묻는다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

제품은 답을 만들기 전에 PDF 원문을 잃지 않는 단위로 보존하고, 나중에 질문이나 extraction target으로 관련 source unit을 찾을 수 있는 index를 준비해야 한다.

## RAG 기본 흐름

```text
StoredMaterial(text, fileName, pageCount)
-> SourceUnit[]
-> IndexRecord[]
-> embedding / vector index / lexical index
-> RetrievalCandidate[] / ContextPack
-> 03 grounding + Evidence-backed fact
```

TripProof에서 이 흐름의 소유권은 아래처럼 나눈다.

- 02는 `SourceUnit`과 `IndexRecord`를 만든다.
- embedding/vector/lexical index는 source unit을 찾기 위한 파생물이다.
- retrieval candidate와 context pack은 아직 사용자-facing evidence가 아니다.
- accepted evidence와 `supported` / `missing` 판단은 03에서 source unit 원문을 다시 확인한 뒤 만든다.

## Goal

- source unit 생성 입력은 01에서 파싱된 PDF 본문을 받는다.
- 파싱 본문은 `materialId`, `fileName`, `page`, `unitIndex`, `locator`, `text`를 가진 source unit으로 나뉜다.
- 각 source unit은 나중에 원문 일부를 그대로 snippet으로 회수할 수 있어야 한다.
- index record는 source unit을 가리키는 stable ref와 검색용 text/metadata를 가진다.
- embedding vector를 만들더라도 vector는 source unit을 찾기 위한 색인이고, 근거 자체가 아니다.
- 등록되지 않은 companion source의 값은 현재 PDF source unit이나 index record로 섞지 않는다.

## Rules

- source unit은 답변, fact, accepted evidence가 아니다. 원문을 다시 찾기 위한 최소 근거 단위다.
- index record는 source unit에서 파생된다. 원문 truth의 주인은 항상 source unit text와 locator다.
- embedding/vector DB를 붙여도 `vector -> sourceUnitId -> SourceUnit.text`로 되돌아올 수 있어야 한다.
- lexical search, embedding search, rerank는 모두 retrieval 후보를 만들기 위한 방법일 뿐, `supported`를 결정하지 않는다.
- source unit은 최소한 `materialId`, `fileName`, `page`, `unitIndex`, `locator`, `text`를 가진다.
- index record는 최소한 `sourceUnitId`, `materialId`, `locator`, `embeddingText` 또는 `searchText`를 가진다.
- 체크인 제시물, 체크인 시작 시각, 날짜 같은 도메인 target 판정은 02에 넣지 않는다.
- 질문 히스토리나 일반 호텔 지식으로 현재 등록된 source boundary를 넓히지 않는다.

## Non-goals

- 체크인 제시물, 체크인 날짜, 체크인 시작 시각 판정.
- evidence source 선택이나 rejected candidate 판정.
- `TripFact`, `EvidenceRef`, `EvidenceState` 생성.
- 답변 문장 생성, 카드 초안, 대시보드, 현장 카드.
- 특정 vector DB 제품 선택이나 운영 스택 확정.
- 모든 PDF 형식에 맞는 semantic chunking.
- OCR, bbox, visual region locator.
- eval metric dashboard.

## 현재 코드에서 볼 곳

- `apps/server/app.py`: `MaterialStore`가 앱 상태에 연결된다.
- `apps/server/materials/pdf.py`: PDF text가 `[page N]` 마커와 함께 만들어진다.
- `apps/server/materials/store.py`: ready material의 `text`, `file_name`, `page_count`가 보관된다.
- `apps/server/retrieval/chunking.py`: source unit 생성 경계가 들어갈 자리.
- `apps/server/retrieval/search.py`: 현재 질문 API가 쓰는 excerpt 선택 helper. 02 구현에서 체크인 도메인 규칙을 여기에 넣지 않는다.
- `apps/server/api/routes/questions.py`: ready material text가 질문 흐름으로 들어가는 곳.

## 기본 흐름

```text
StoredMaterial(text, fileName, pageCount)
-> SourceUnit(materialId, fileName, page, unitIndex, locator, text)
-> IndexRecord(sourceUnitId, materialId, locator, searchText, metadata)
-> optional EmbeddingRecord(sourceUnitId, vector, model)
```

02의 관찰 대상은 source unit과 index record가 원문 위치를 보존하는지다. Retrieval score, evidence selection, rejected candidate, evidence state는 03 이후의 관찰 대상이다.

## 이번 AC

1. 파싱된 PDF 본문은 page locator를 가진 source unit으로 나뉜다.
2. source unit의 `text`는 실제 PDF 파싱 본문 일부이며, snippet으로 그대로 회수할 수 있다.
3. source unit은 `materialId`, `fileName`, `page`, `unitIndex`, `locator`, `text`를 가진다.
4. index record는 source unit을 가리키는 ref와 검색용 text/metadata를 가진다.
5. embedding/vector record를 만들더라도 source unit ref를 통해 원문으로 되돌아올 수 있다.
6. 등록되지 않은 companion source는 source unit이나 index record에 섞이지 않는다.

## 남은 판단

- 첫 source unit granularity를 page 단위로 둘지, page 안 section/문장 단위로 나눌지.
- `sourceUnitId`를 material-local index로 둘지, content hash를 섞은 stable id로 둘지.
- index record를 in-memory로 둘지, 별도 store abstraction을 둘지.
- 첫 embedding provider를 지금 붙일지, embedding record schema만 먼저 닫을지.
- lexical index와 vector index를 같은 abstraction으로 둘지, retrieval 단계에서 합칠지.
