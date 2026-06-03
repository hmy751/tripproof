# Spec

이 폴더는 여러 작업으로 이어지는 설계 맥락을 남길 때만 쓴다.

작은 수정마다 spec을 만들 필요는 없다. 나중에 다시 봐야 할 목표, 제약, 결정, 남은 쟁점만 짧게 남긴다.

## Light spec-driven loop

TripProof의 spec-driven은 문서 gate가 아니라 큰 slice를 작게 잡기 위한 작업 루프다.

큰 slice이면 작업 시작 전에 5줄 정도의 brief를 둔다.

```text
why-now:
의도:
가설/위험:
selected acceptance:
열린 질문 또는 사람 판단 결과:
```

큰 slice의 기준은 실패했을 때 원인과 판단이 흐려지는가다. 사용자 flow가 바뀌거나, AI 위임 범위가 크거나, acceptance가 애매하거나, 실패 유형 분해가 필요하거나, 다음 세션이 이어받아야 하면 큰 slice로 본다.

작은 작업은 별도 spec 없이 바로 진행한다. 오타, 좁은 UI 조정, 기존 acceptance 안의 bugfix, 작은 refactor, 테스트 보강은 commit, PR, test output 근처에 남기는 것으로 충분하다.

`selected acceptance`는 기본 1-3개로 제한한다. spec은 작업을 만들지 않고, 이미 선택한 사용자 장면을 좁히는 데만 쓴다.

새 spec 파일은 여러 세션으로 이어지는 product behavior 기준이 필요하거나, acceptance drift가 반복되거나, 사용자-facing 실패 유형을 분리해야 할 때만 만든다.

권장 형식:

```md
# Slice 이름

## 목표

## 입력과 출력

## 동작 기준

## 결정

## 남은 쟁점

## 검증 후보
```
