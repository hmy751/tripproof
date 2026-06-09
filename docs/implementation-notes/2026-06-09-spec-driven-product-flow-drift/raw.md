# Raw Notes - Spec-driven slice와 제품 흐름 drift

이 파일은 `index.md` 관찰의 배경 재료다. 현재 실행 기준이나 작업 대기열이 아니다.

## 왜 raw가 필요한가

이번 관찰은 단일 문구 수정에서 나온 것이 아니라, 숙소 체크인 04 구현 준비 과정에서 두 흐름을 비교하며 생겼다. 하나는 scope control을 먼저 적용한 흐름이었고, 다른 하나는 같은 04 맥락에서 제품 경로를 먼저 고정한 흐름이었다.

비교의 목적은 특정 응답을 평가하는 것이 아니라, scope 축소 전에 제품 흐름을 먼저 고정해야 하는지 확인하는 것이었다. 결론은 `spec-driven` 자체를 폐기하는 것이 아니라, scope를 줄이기 전에 제품 흐름을 먼저 고정해야 한다는 쪽으로 좁혀졌다.

## 대화·조사에서 드러난 문제 감각

scope를 먼저 줄이는 흐름에서는 04를 `facts[]를 사용자-facing ChatAnswer처럼 보여주는 단계`로 잡았지만, 동시에 더 작은 단계로 줄이면 `client가 facts[]를 렌더링하고 ChatAnswer schema는 후속 단계로 미루는` 대안이 나왔다.

이 표현은 개발 병목으로 이어질 수 있다. 제품 기능 적용 대신 raw output을 화면에 붙이고, 목업이나 debug 표시가 제품 확인처럼 보일 수 있기 때문이다. 문제는 scope control 자체가 아니라, scope control이 제품 흐름을 자르는 방향으로 해석될 수 있다는 점이었다.

발동되지 않은 흐름은 다음 경로를 더 선명하게 잡았다.

```text
QuestionRequest
-> ready materials
-> retrieval excerpt
-> fact candidates
-> ChatAnswer 구성
-> client 채팅 UI에 표시
```

또한 금지선을 함께 두었다.

- missing인 체크인 시작 시각을 상식으로 채우지 않는다.
- excerpt만 보고 supported처럼 말하지 않는다.
- fact candidate를 카드나 대시보드에 바로 확정 반영하지 않는다.

이 비교에서 드러난 차이는 skill 발동 여부 자체보다, 제품 흐름을 먼저 잡았는지와 scope control을 먼저 잡았는지의 차이에 가까웠다.

## 확인된 사실과 해석

`spec-driven`의 좋은 점은 유지되어야 한다.

- 작은 작업을 불필요한 spec gate로 만들지 않는다.
- 큰 작업을 사용자 장면과 관찰 가능한 AC로 좁힌다.
- eval이나 문서가 product보다 앞서지 않게 한다.
- fixture, hard-coded answer, stub이 제품 확인을 대신하지 않게 한다.

그러나 `작게`, `얇게`, `slice`, `AC 1-3개`, `화면까지` 같은 표현은 제품 흐름 없이 쓰이면 가장 빨리 보이는 화면 조각으로 미끄러질 수 있다. 이때 좋은 slice와 나쁜 slice의 경계가 흐려진다.

이번 사례에서 좋은 slice는 `FactCandidate[] -> ChatAnswer -> 채팅 UI` 변환을 통과한다. 나쁜 slice는 `facts[]` raw 렌더링을 제품 답변처럼 취급한다.

## 기각·보류된 후보

기각한 방향:

- `spec-driven`을 무거운 승인 절차로 되돌리는 것.
- 모든 stub, deterministic adapter, debug view를 금지하는 것.
- AC 개수를 늘려 문제를 해결하려는 것.
- 냄새 신호만 길게 늘리고 실행 전 판단 순서를 바꾸지 않는 것.

보류한 방향:

- `docs/specs/README.md`까지 즉시 같은 문구로 확장하는 것. 같은 문제가 반복적으로 확인되면 별도 문서 정리 대상으로 판단한다.
- 04 spec에 `ChatAnswer` 계약을 더 명시하는 것. 이는 04 구현을 시작할 때 별도 작업으로 판단한다.

## 재진입 메모

비슷한 상황에서 다음 질문을 먼저 본다.

```text
입력:
변환:
출력:
넘지 말 선:
```

이 네 줄은 문서 gate가 아니라 흐름을 자르기 전에 보는 안전장치다. 어디서 잘라도 되는지 애매하면 AI가 결정하지 말고 사용자에게 확인한다.
