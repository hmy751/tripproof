# Fixtures

TripProof fixture는 product와 eval이 함께 쓰는 안전한 sample material이다.
단순 JSON mock이 아니라, 사용자가 넣은 자료처럼 다룰 수 있는 원본형 자료와
그 자료에서 기대되는 결과를 역할별로 나눈다.

## Structure

```text
fixtures/
  accommodation-checkin/
    manifest.json
    input/
      booking-confirmation.pdf
      host-message.txt
    extracted/
      booking-confirmation.txt
      host-message.txt
    expected/
      facts.json
      answers.json
```

fixture는 자료 묶음 단위로 둔다. 예를 들어 `fixtures/accommodation-checkin/`은
숙소 체크인 확인에 필요한 자료 묶음 하나다.

- `input/`: 사용자가 실제로 보는 원본형 자료. PDF, email, message, receipt
  같은 sanitized 파일을 둔다.
- `extracted/`: parser, OCR, email extractor 이후 엔진이 보는 텍스트 입력.
  첫 구현에서는 수동으로 만든 text를 둘 수 있고, 나중에는 실제 추출기가 생성한다.
- `expected/`: 같은 input에서 나와야 하는 `TripFact`, 대표 답변, evidence state.
- `manifest.json`: input 파일, extracted 파일, 표시 이름, 자료 종류를 연결하는 인덱스.

## Material Handling

- fixture는 실제 자료의 형태와 문장을 가능한 한 유지한 sanitized copy를 우선한다. 새로 꾸민 synthetic text는 원본 구조를 보존할 수 없을 때만 쓴다.
- 민감하거나 개인을 식별할 수 있는 값은 무효 placeholder로 바꾼다.
- 마스킹 전 원본, 실제 식별자, 원본과 sanitized 파일의 상세 매핑표는 commit하지 않는다.
- `expected/`는 `input/`과 `extracted/`에서 근거를 찾을 수 있는 값만 담는다.
- 이 기준은 자료 위생 기준이다. fixture 파일이나 expected output만 준비하고 product slice가 통과했다고 말하지 않는다.
