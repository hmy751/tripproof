# 개발 노트

TripProof는 먼저 작게 동작하는 product path를 만들고, 그 뒤에 관찰과 평가를 붙인다.

## 기본 방향

- 사용자가 넣은 자료에서 확인 가능한 정보를 보여준다.
- 근거가 부족하거나 자료가 충돌하면 그 상태를 드러낸다.
- 계획 중인 기능이나 평가 결과를 구현된 것처럼 설명하지 않는다.

## Product와 Eval

product 쪽은 사용자에게 보이는 흐름과 결과 계약을 가진다.

- 입력 자료
- 추출된 정보
- 원문 근거
- 불확실성 또는 충돌 상태
- UI와 eval이 함께 읽을 수 있는 결과 형태

eval 쪽은 product를 관찰한다.

- product entry point를 호출한다.
- 결과와 실패 양상을 기록한다.
- product 로직을 중복 구현하지 않는다.

## 기록 기준

문서는 필요한 만큼만 남긴다.

- 작은 구현 판단은 코드, commit, PR 설명 가까이에 둔다.
- 이후 구조를 바꾸는 선택은 `docs/decisions/`에 둔다.
- 여러 작업으로 이어지는 설계 맥락만 `docs/specs/`에 남긴다.
- 구현 중 반복해서 다시 볼 오해, drift, 경계 관찰은 `docs/implementation-notes/`에 둔다.
- eval run 기록은 실제 product behavior를 관찰할 수 있을 때 남긴다.
