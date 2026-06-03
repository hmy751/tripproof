# Product Server

server는 client가 부르는 product entry point를 둔다.

- route/action은 사용자 입력 자료를 받고 product 결과 계약으로 돌려준다.
- AI 호출, 파일 파싱, 저장소 접근은 server 내부 구현으로 숨긴다.
- eval fixture, run artifact, metric output에 의존하지 않는다.

초기 구조:

- `trip-facts/` — Python 후보나 deterministic 후보를 `TripProofResult`로 정규화하는 TS server 경계.
- `../shared/` — client와 server가 함께 읽는 결과 타입.
