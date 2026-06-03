# Raw Notes - Light spec-driven loop 운영

이 파일은 `index.md` 결정의 배경 재료이며, 당시 상황의 생생함을 보존하기 위한 자료다. 현재 실행 기준이나 작업 대기열이 아니다.

## 왜 raw가 필요한가

이 결정은 단순히 `docs/specs/README.md`에 규칙을 추가한 작업이 아니었다. 사용자는 TripProof 문서 개편 뒤 spec-driven 의도가 희석됐는지, 그리고 기존 실행력 문제를 다시 만들지 않으면서 회사들이 요구하는 역량을 어떻게 보여줄 수 있을지 확인하려 했다. 이 raw는 그때의 압력, 정정, 우려, 선택 감각을 다음 세션이 잃지 않도록 남긴다.

대화는 다음 재료를 거쳤다.

- 최종 합의본의 spec-driven, product-first, eval 관찰 원칙.
- 그 합의본 이전의 원본 대화, 회사 요구 신호, 외부 방법론 추적 결과.
- 별도 조사와 검토: 참고자료 요약, 현재 repo 문서 상태, 문서 boundary, anchor 위험, 최종 출처 추적, 근거 점검, 운영 원칙 점검.
- 사용자의 정정: 폐기된 부산물을 다시 중심에 두지 말 것, 당연한 공개 경계 논의로 새지 말 것, spec-driven이 최종 생존 후보라는 점을 볼 것.

따라서 결론만 `index.md`에 남기고, 판단의 배경과 오해 방지 재료는 이 raw에 격리한다.

## 대화·조사에서 드러난 문제 감각

처음에는 현재 문서 개편이 spec-driven 의도를 너무 낮춘 것인지가 문제처럼 보였다. 조사 결과, spec-driven 자체는 사라진 것이 아니라 실행 권한을 낮추는 과정에서 실제 구현 brief와의 연결이 약해질 수 있다는 쪽으로 문제가 좁혀졌다.

사용자는 이후 한 가지를 더 정정했다. 최종 합의본만 보면 결론에 맞춰 읽히므로, 그 전의 회사 요구 신호, 원본 대화, 외부 방법론까지 따라가 spec-driven이 왜 남았는지 봐야 한다는 점이었다.

추적 결과의 요지는 다음과 같았다.

- TripProof의 spec-driven은 공고 키워드를 product 동기로 역수입한 것이 아니다.
- AI 학습과 작업 과정에서 생긴 신뢰성, 실패 유형 분해, 근거 있는 개선 감각이 먼저 있었다.
- 회사 요구에서 읽힌 신호는 그 감각을 설명할 수 있는 역량 프레임으로 작동했다.
- 남은 핵심은 `prompt-brief + acceptance 기준 + human judgment + product-first eval/failure loop`다.
- full SDD, Spec Kit, constitution, 모든 작업 spec화는 product 실행을 밀어낼 위험 때문에 기본값에서 빠졌다.

## 출처와 확인된 사실

별도 근거 점검에서 강하게 확인된 주장:

- product-first / eval은 관찰자라는 방향은 로컬 repo 지침과 이전 합의 문서에서 반복된다.
- full SDD/Spec Kit 도입이 아니라 prompt-brief/light spec 수위로 낮춘다는 흐름은 이전 spec 위임 합의와 일치한다.
- AI 위임의 핵심은 AI output 자체가 아니라 사람의 채택/기각 판단이다.
- 폐기된 작업 메타나 AI 사용량 기록을 active proof로 되살리지 않는 방향은 합의 문서와 맞다.

해석 여지가 있는 주장:

- light spec은 현재 유력한 기본값이지만 영구 결론은 아니다. 여러 사람이 같은 slice를 반복 위임하거나 품질 regression이 누적되면 일부 toolkit을 다시 볼 수 있다.
- 회사 요구와 TripProof 연결은 직접 요구가 아니라 로컬 해석이다. 회사들이 TripProof의 특정 spec-driven 구조를 요구했다고 쓰면 비약이다.

추가 확인이 남은 것:

- 일부 시간축과 원문 역추적 결과는 조사 보고에서 제시됐지만, 이 decision에서는 commit 단위 재검증까지 하지는 않았다.
- eval run artifact 구조나 metric threshold는 주력 증거 후보일 수 있으나 계약으로 확정하지 않는다.

## 기각·보류된 후보

이번 대화에서 반복적으로 접은 부산물과 샛길은 아래 정도로만 기억한다. 이 항목들은 현재 후보가 아니다.

- 폐기된 AI 작업 메타를 proof로 되살리는 방식.
- 외부 준비 맥락을 어떻게 노출할지 같은 공개 경계 논의.
- 외부 요구 신호 때문에 Spec Kit/SDD를 도입해야 한다는 해석.
- 모든 작업에 spec/log/eval을 붙이는 방식.
- GraphRAG, OCR, confidence schema, eval/runs 4파일 계약 같은 후속 구현 후보를 지금 닫는 방식.
- TripProof 전용 skill을 글로벌 skill로 만드는 방식.

중요한 정정:

처음에는 `tripproof-spec-driven` skill을 글로벌 skill처럼 만들었다. 사용자가 "프로젝트 전용으로 만들어야지"라고 정정했고, repo-local skill로 다시 정리했다.

정리 후 상태:

- 전역 등록은 제거하고, repo-local `.claude/skills/tripproof-spec-driven`과 `.codex/skills/tripproof-spec-driven` symlink로 정리했다.
- `bridge-auditor` 확인 결과, 현재 지침 원천에는 전역 등록이 남지 않았고 repo-local bridge 구조와 맞는 것으로 보고됐다.

## 남은 불확실성

- 큰 slice 기준을 실제 작업에서 얼마나 엄격하게 적용할지.
- `selected acceptance`를 기본 1-3개로 제한했을 때, 어느 경우에 예외를 둘지.
- brief를 대화, PR, commit, work-log 중 어디에 남기는 것이 가장 덜 무거운지.
- product 실행 지점이 생기기 전 eval 후보를 어디까지 설계해도 되는지.

## 당시 재진입 메모

아래는 당시 대화를 정리하며 남긴 요약이다. 현재 실행 지시가 아니라 `index.md` 결정을 이해하기 위한 배경 문장이다.

> TripProof의 spec-driven은 문서 생산 방식이 아니라, 큰 AI 위임 전에 의도와 통과 기준을 얇게 고정하고 사람이 결과를 회수해 product behavior로 되돌리는 운영 루프다.

이 요약을 현재 작업에 적용하려면 `index.md`의 결정과 현재 코드 상태를 다시 함께 본다.
