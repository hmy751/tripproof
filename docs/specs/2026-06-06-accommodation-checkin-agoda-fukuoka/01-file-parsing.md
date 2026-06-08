# 숙소 체크인 01 - Agoda PDF 파일 파싱

상태: first backend slice implemented.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

제품의 시작은 사용자가 원본 자료 파일을 넣고, 제품이 그 파일에서 본문을 얻는 것이다. 이 단계는 Agoda 예약 확정 PDF 하나를 제품에 넣고, 파싱된 본문이 자료함과 다음 source/evidence 단계 입력으로 이어지는 데까지를 닫는다.

## 사용자 장면

사용자는 Agoda 후쿠오카 숙소의 `예약 확정 PDF`를 제품에 넣는다. 파일이 들어오면 사용자는 바로 체크인 준비 질문을 할 수 있어야 한다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

## Goal

- 사용자가 Agoda 예약 확정 PDF 하나를 선택하거나 추가할 수 있다.
- 제품은 PDF에서 텍스트 본문을 읽는다.
- 자료함에는 파일명, 자료 종류, 파싱 상태, page 수가 보인다.
- 파싱된 본문은 source unit/RAG search와 evidence-backed fact 단계가 읽을 수 있는 상태로 저장된다.
- 파싱 본문에는 예약 확정서 제시 안내, 체크인/체크아웃 날짜, 취소/노쇼 정책, 도시세 안내, 신분증/카드 제시 안내가 들어간다.
- 근거 source로 확인되지 않은 체크인 관련 값을 성공한 것처럼 만들지 않는다.
- PDF 파싱이 실패하면 실패 상태가 보이고, 조용히 성공한 것처럼 넘어가지 않는다.

## Rules

- client는 React/Vite 화면에서 PDF 파일을 선택하고 backend로 전송한다.
- PDF text extraction은 Python backend ingest가 맡는다.
- 첫 제품 입력은 `.pdf` 원본이다. `.txt`나 `.md`로 미리 변환한 파일을 product proof의 입력으로 삼지 않는다.
- PDF binary 읽기, PDF text extraction, 자료함 item 생성, 다음 source/evidence 입력 생성을 분리한다.
- 처음은 텍스트 추출 가능한 1페이지 PDF를 대상으로 한다.
- PDF 본문 없이 질문에 답하지 않는다.
- attachment id, Gmail message id, private booking URL은 자료함 item이나 공개 fixture에 저장하지 않는다.

## Non-goals

- Gmail 계정에서 PDF 자동 가져오기.
- Agoda 앱이나 웹 예약 페이지 자동 수집.
- 스캔 이미지 PDF OCR.
- PDF 표 레이아웃 완전 복원.
- 파일 장기 저장과 계정 동기화.
- Agoda HTML 메일 본문을 같은 자료로 자동 병합하기.

## 이번 AC

1. 사용자가 Agoda 예약 확정 PDF 하나를 넣을 수 있다.
2. 자료함에 PDF가 파싱 완료 상태로 보인다.
3. 질문 입력이 자료 없음 상태로 막히지 않는다.
4. source/evidence 입력에는 실제 PDF에서 파싱된 본문이 들어간다.
5. 체크인 시작 시각에 대한 근거 source가 없으면 값을 임의로 넣지 않는다.

## 구현 메모

이번 구현은 client-side PDF 파싱이 아니라 Python backend ingest 경로로 진행한다.

- client는 PDF 선택, 업로드 요청, 파싱 상태 표시만 맡는다.
- backend는 PDF binary를 받아 text와 page count를 추출하고, 이후 질문 단계가 읽을 수 있는 material text로 보관한다.
- 첫 저장소는 in-memory로 둔다. DB, 계정 동기화, 장기 파일 저장은 열지 않는다.
- 질문 API는 ready material의 파싱 본문이 다음 source/evidence 입력으로 넘어가는지만 01에서 확인한다. source unit, embedding record, retrieval 후보, fact, 답변 문장, 인라인 근거 UI, 카드 초안은 02 이후에서 다룬다.
- 기존 TS 중심 `src/server/trip-facts`, `src/shared`, `src/ai` 구조는 Python backend 전환 중 남겨둘 호환용 계층이 아니라 삭제/흡수 대상으로 본다.

## 구현 상태

- `apps/server/` Python backend가 `/api/materials`, `/api/questions`를 제공한다.
- `uv`와 `uv.lock`으로 backend 의존성을 고정한다.
- client는 PDF를 backend로 전송하고 ready/failed 상태를 자료함에 표시한다.
- 질문 API는 ready material의 파싱 본문을 context로 받는 데까지만 닫았다.
- 기존 `src/ai`, `src/server/trip-facts`, `src/shared` 경로는 삭제했다.

## 남은 판단

- 공개 fixture 파일명은 `agoda-fukuoka-booking-confirmation.pdf`처럼 둘지.
- 파싱 본문 preview를 자료함에 얼마나 보여줄지.
