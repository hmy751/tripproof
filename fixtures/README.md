# Sample Materials

TripProof 개발 중에 쓰는 공개 가능한 sample 자료를 둔다.
여기 있는 파일은 제품 흐름을 확인하기 위한 입력 예시일 뿐, 구현 전에 반드시 맞춰야 하는 준비물이 아니다.

## Structure

```text
fixtures/
  accommodation-checkin/
    agoda-booking-confirmation-sample.txt
    agoda-fukuoka-checkin-start-1600.txt
```

sample 자료는 장면 단위로 둔다. 예를 들어 `fixtures/accommodation-checkin/`은
숙소 체크인 확인에 필요한 예약 확인서와 호스트 메시지 예시를 담을 수 있다.

파일명과 폴더 구조는 구현이 필요로 할 때 단순하게 정한다.

## Material Handling

- 이 디렉터리에는 repo에 둘 수 있는 공개 sample 입력만 둔다.
- 공개 sample에는 실제 예약번호·주소·연락처·결제정보 같은 식별값을 그대로 남기지 않고 마스킹한다. 실제 민감 자료는 `fixtures/private/`(gitignore)에 두고 commit하지 않는다. 이 경계는 제품 기능 제한이 아니라 공개 자료 관리 기준이다 (`docs/decisions/2026-06-09-sensitive-data-fixture-boundary.md`).
- sample 자료를 만들었다고 product flow가 완성된 것으로 보지 않는다.
