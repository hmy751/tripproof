# 엔지니어링 문서

코드 개발의 판단 기준을 모은 폴더다. 강제 관문이 아니라 참고 기준이다.

## 문서

- `principle.md` — 설계·변경·추상화 원칙.
- `architecture.md` — 현재 모듈 지도와 경계.
- `testing.md` — 검증의 종류와 테스트.
- `ai-coding.md` — AI가 코드를 만들 때의 규율.

## 기록 기준

문서는 필요한 만큼만 남긴다.

- 작은 구현 판단은 코드·commit·PR 설명 가까이에 둔다.
- 이후 구조에 영향을 주는 선택은 `docs/decisions/`에 둔다.
- 여러 작업에 이어지는 설계 맥락은 `docs/specs/`에 둔다.
- 구현 중 반복해 다시 볼 오해·drift·경계 관찰은 `docs/implementation-notes/`에 둔다.
- eval run 기록은 실제 product behavior를 관찰할 수 있을 때 남긴다.
