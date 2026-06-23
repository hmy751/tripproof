# 엔지니어링 문서

이 폴더는 TripProof의 engineering taste와 trade-off를 맞추기 위한 calibration reference다.
각 문서는 모든 코드 변경마다 통과해야 하는 gate나 체크리스트가 아니라, 설계 판단이 흔들릴 때 꺼내 보는 lens다.

제품 동작의 강제는 테스트와 실제 product behavior 확인이 맡는다. 이 문서들은 테스트로 잘 잡히지 않는 구조적 위험과 경계 판단을 돕는다.

## 언제 무엇을 보나

- 설계·추상화·실패 처리를 정할 때 → `principle.md`
- 코드를 어디에 둘지, 의존 방향이 헷갈릴 때 → `architecture.md`
- 무엇으로 동작을 확인할지 → `testing.md`
- AI에게 코드를 맡길 때 → `ai-coding.md`

## 사용 방식

- 변경이 어떤 경계를 건드리는지 먼저 판단한다.
- 해당되는 문서만 읽고, 현재 작업에 적용되는 원칙을 짧게 고른다.
- 원칙이 구현을 막는 체크리스트가 되면 사용자 요청, 관련 spec/AC, 실제 product behavior로 돌아간다.
- 좁은 UI, 문구, 스타일, 지역 함수 수정은 주변 코드 패턴과 관련 테스트를 우선한다.
