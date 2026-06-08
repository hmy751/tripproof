# 숙소 체크인 02 - Source unit과 근거 후보 검색

상태: sub-spec draft.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

PDF 본문을 긴 문자열 하나로 AI에 넘기면, 답변이 실제 원문 어디에서 왔는지 추적하기 어렵다. 이번 단계는 01에서 파싱한 PDF 본문을 page/section/source unit으로 나누고, 체크인 질문이나 필드 목표에 맞는 근거 후보를 찾은 뒤, 실제로 채택한 source와 탈락한 candidate를 분리하는 데까지를 닫는다.

이 단계는 최종 답변이나 카드가 아니라, `근거 있음`을 주장하기 전에 통과해야 하는 grounding boundary다.

## 사용자 장면

사용자는 Agoda 예약 확정 PDF를 넣고 전체 자료함에 묻는다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

제품은 답을 만들기 전에 PDF 안에서 이 질문과 관련된 원문 단위를 찾아야 한다.

## Goal

- source unit 생성 입력은 01에서 파싱된 PDF 본문을 받는다.
- 파싱 본문은 `materialId`, 파일명, page, locator, text를 가진 source unit으로 나뉜다.
- 체크인 제시물, 체크인 날짜, 체크인 시작 시각 같은 목표별로 retrieval candidate를 만들 수 있다.
- candidate 전체와 실제 채택한 accepted source를 분리한다.
- accepted source의 snippet은 실제 PDF 파싱 본문 일부다.
- 체크인 제시물 안내는 PDF 본문에서 accepted source를 찾을 수 있다.
- 체크인 시작 시각은 관련 source unit이 accepted될 때만 이후 fact의 근거가 된다.
- 등록되지 않은 companion source의 값은 현재 PDF source unit이나 accepted source로 섞지 않는다.

## Rules

- source unit은 답변이나 fact가 아니다. 원문을 다시 찾기 위한 최소 근거 단위다.
- accepted source는 아직 `근거 있음` fact가 아니다. 03에서 `TripFact`와 `EvidenceState`로 변환된다.
- 처음 구현은 keyword/section 기반 retrieval이어도 된다. 다만 자료가 바뀌면 candidate와 accepted source도 바뀌어야 한다.
- 나중에 embedding, vector DB, rerank를 붙여도 `candidate -> accepted source -> evidence` 계약은 유지한다.
- source unit은 최소한 `materialId`, `fileName`, `page`, `unitIndex`, `locator`, `text`를 가진다.
- retrieval candidate는 source unit과 함께 target, score 또는 match reason, accepted 여부를 관찰 가능하게 남긴다.
- rejected candidate는 debug/observation 재료일 수 있지만 사용자-facing evidence가 아니다.
- 질문 히스토리나 일반 호텔 지식으로 현재 등록된 source boundary를 넓히지 않는다.

## Non-goals

- vector DB, HyDE, BM25/RRF, LLM rerank 전체 스택.
- 모든 PDF 형식에 맞는 semantic chunking.
- OCR, bbox, visual region locator.
- fact 생성, 상태 판정, 답변 문장 생성.
- 카드 초안, 대시보드, 현장 카드.
- eval metric dashboard.

## 현재 코드에서 볼 곳

- `apps/server/app.py`: `MaterialStore`가 앱 상태에 연결된다.
- `apps/server/materials/pdf.py`: PDF text가 `[page N]` 마커와 함께 만들어진다.
- `apps/server/materials/store.py`: ready material의 `text`, `file_name`, `page_count`가 보관된다.
- `apps/server/retrieval/chunking.py`: retrieval/chunking 경계가 들어갈 자리.
- `apps/server/retrieval/search.py`: 현재 질문 API가 쓰는 excerpt 선택 helper.
- `apps/server/api/routes/questions.py`: ready material text가 질문 흐름으로 들어가는 곳.

## 기본 흐름

```text
StoredMaterial(text, fileName, pageCount)
-> SourceUnit[]
-> target별 RetrievalCandidate[]
-> accepted source / rejected candidate 분리
-> 03 evidence-backed facts 입력
```

candidate 전체, accepted source, 사용자-facing evidence, 내부 observation/debug 재료를 분리한다. TripProof에서는 이 구조를 답변 중심이 아니라 evidence state를 만들기 위한 source boundary로 쓴다.

## 이번 AC

1. 파싱된 PDF 본문은 page locator를 가진 source unit으로 나뉜다.
2. 체크인 제시물 목표는 PDF 본문에서 accepted source를 찾고, snippet은 실제 PDF 본문 일부다.
3. 체크인 제시물 안내 문장을 파싱 본문에서 제거하면 accepted source가 나오지 않는다.
4. 등록된 source unit에서 근거가 잡히지 않은 time value를 accepted source로 만들지 않는다.
5. candidate 전체와 accepted/rejected 구분은 observation/debug용으로 확인 가능하다.

## 남은 판단

- 첫 source unit granularity를 page 단위로 둘지, page 안 section/문장 단위로 나눌지.
- candidate score를 숫자로 둘지, match reason 문자열 중심으로 둘지.
- accepted/rejected 후보를 API response에 바로 노출할지, backend 내부 관찰값으로만 둘지.
- companion source가 열릴 때 multi-document retrieval을 02 확장으로 볼지 별도 spec으로 뺄지.
