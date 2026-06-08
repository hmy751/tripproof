# Sample Materials

TripProof 개발 중에 쓰는 공개 가능한 sample 자료를 둔다.
여기 있는 파일은 제품 흐름을 확인하기 위한 입력 예시일 뿐, 구현 전에 반드시 맞춰야 하는 준비물이 아니다.

## Structure

```text
fixtures/
  accommodation-checkin/
    booking-confirmation.txt
    host-message.txt
```

sample 자료는 장면 단위로 둔다. 예를 들어 `fixtures/accommodation-checkin/`은
숙소 체크인 확인에 필요한 예약 확인서와 호스트 메시지 예시를 담을 수 있다.

파일명과 폴더 구조는 구현이 필요로 할 때 단순하게 정한다.

## Material Handling

- 실제 값을 옮기지 않고 placeholder를 쓴다.
- 실제 원본, 실제 식별자, 원본과 sample 파일의 상세 매핑표는 commit하지 않는다.
- sample 자료를 만들었다고 product flow가 완성된 것으로 보지 않는다.
