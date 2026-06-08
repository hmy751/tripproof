# 숙소 체크인 01 - Agoda PDF 파일 파싱

상태: sub-spec draft.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

제품의 시작은 사용자가 원본 자료 파일을 넣고, 제품이 그 파일에서 본문을 얻는 것이다. 이 단계는 Agoda 예약 확정 PDF 하나를 제품에 넣고, 파싱된 본문이 자료함과 AI 해석 입력으로 이어지는 데까지를 닫는다.

## 사용자 장면

사용자는 Agoda 후쿠오카 숙소의 `예약 확정 PDF`를 제품에 넣는다. 파일이 들어오면 사용자는 바로 체크인 준비 질문을 할 수 있어야 한다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

## Goal

- 사용자가 Agoda 예약 확정 PDF 하나를 선택하거나 추가할 수 있다.
- 제품은 PDF에서 텍스트 본문을 읽는다.
- 자료함에는 파일명, 자료 종류, 파싱 상태, page 수가 보인다.
- 파싱된 본문은 AI 해석 단계가 읽을 수 있는 상태로 저장된다.
- 파싱 본문에는 예약 확정서 제시 안내, 체크인/체크아웃 날짜, 취소/노쇼 정책, 도시세 안내, 신분증/카드 제시 안내가 들어간다.
- 파싱 본문에 없는 체크인 시작 시각을 성공한 것처럼 만들지 않는다.
- PDF 파싱이 실패하면 실패 상태가 보이고, 조용히 성공한 것처럼 넘어가지 않는다.

## Rules

- client는 React/Vite 화면에서 PDF 파일을 받는다.
- 첫 제품 입력은 `.pdf` 원본이다. `.txt`나 `.md`로 미리 변환한 파일을 product proof의 입력으로 삼지 않는다.
- PDF binary 읽기, PDF text extraction, 자료함 item 생성, AI 해석 입력 생성을 분리한다.
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
4. AI 해석 입력에는 실제 PDF에서 파싱된 본문이 들어간다.
5. PDF 파싱 본문에서 체크인 시작 시각이 없으면 `15:00` 같은 값을 임의로 넣지 않는다.

## 남은 판단

- PDF text extraction을 client에서 `pdf.js`로 처리할지, server/helper 모듈로 분리할지.
- 공개 fixture 파일명은 `agoda-fukuoka-booking-confirmation.pdf`처럼 둘지.
- 파싱 본문 preview를 자료함에 얼마나 보여줄지.
