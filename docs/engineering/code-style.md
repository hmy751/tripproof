# 코드 스타일

이 문서는 formatter와 code review의 책임을 나누기 위한 기준이다. 스타일을 새 gate로 늘리기보다, 기계가 맞출 수 있는 것은 기계에 맡기고 사람이 읽는 흐름은 리뷰에서 본다.

## 강제 포맷

- Python은 Black을 기준으로 한다. 실행 명령과 설정은 루트 `AGENTS.md`, `package.json`, `pyproject.toml`을 원천으로 본다.
- TypeScript/React는 프로젝트의 formatter, typecheck, build 설정을 따른다. 별도 lint 규칙이 없으면 주변 코드의 패턴을 우선한다.
- formatter가 만든 diff와 사람이 읽기 쉽게 나눈 diff를 구분한다. 포맷 변경만 필요한 경우 동작 변경과 섞지 않는다.

## 읽는 흐름

- formatter가 정하지 않는 영역은 리뷰에서 읽는 흐름을 기준으로 본다.
- 함수 내부 blank line은 논리 단계, 상태 전환, fallback/flush처럼 읽는 단락이 바뀔 때 도움이 될 수 있다.
- guard, 판단, 상태 갱신, 후처리가 한 덩어리로 붙어 알고리즘 흐름이 압축되어 보이면 빈 줄이나 helper로 인지 단락을 드러낼 수 있다.
- 예시는 규칙이 아니라 calibration sample이다. "항상 이렇게 띄운다"가 아니라, 다음 사람이 한 번에 따라올 수 있는지를 본다.
