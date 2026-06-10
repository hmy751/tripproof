# Raw Notes - Surface 이후 Leaf Producer 우선 순서

이 파일은 `index.md` 관찰의 배경 재료다. 현재 실행 기준이나 작업 대기열이 아니다.

## 왜 raw가 필요한가

이번 관찰은 단일 문구 수정에서 나온 것이 아니라, 질문 실행 기록 spec을 다음 구현으로 이어받는 대화에서 반복된 방향 전환을 통해 생겼다. 처음에는 LangSmith trace나 no-op wrapper가 문제처럼 보였지만, 이후 검토에서는 더 넓은 패턴이 드러났다.

핵심 맥락은 운영 문서와 spec이 판단 렌즈로 쓰이지 않고, 제목, 하위 spec 번호, 첫 AC, next slice 같은 구조를 통해 다음 작업 큐처럼 읽힐 수 있다는 점이었다. 이 배경을 모르면 `index.md`의 leaf producer ordering이 단순한 구현 순서 선호처럼 보일 수 있어 raw를 분리해 남긴다.

## 대화·검토에서 드러난 문제 감각

질문 실행 기록 spec은 prompt/config snapshot과 LangSmith 관측 기록을 다루고 있었다. prompt document/runtime 분리가 먼저 정리된 뒤, 다음 작업을 회수하는 과정에서 `LangSmith no-op 안전 wrapper`가 첫 구현 단위처럼 제안됐다.

검토 과정에서 `POST /api/materials` 관측 지점, config/prompt snapshot, `/api/questions` 관측 지점을 먼저 정하고 그 다음 LangSmith를 붙이는 순서가 더 적합하다는 판단이 나왔다. 이후 문제는 LangSmith 자체가 아니라, 큰 시나리오를 가로로 펼친 뒤에도 상위 문서 구조가 특정 provider나 wrapper 아래로 작업을 세로화할 수 있다는 쪽으로 좁혀졌다.

이어진 검토에서는 문서 구조를 작업 큐로 그대로 따르기보다, 현재 product surface에서 필요한 producer로 다시 해석해야 한다는 기준이 정리됐다. 그러나 구현면 펼치기 원칙은 이미 존재했기 때문에, 문장이나 원칙을 더 붙이는 것만으로는 부족하다는 판단이 나왔다. 최종적으로는 surface 이후 첫 구현 대상을 제한하는 ordering rule이 더 직접적인 개입으로 좁혀졌다.

## 대화에서 반복된 표현과 역할

초기에는 `얇게`, `baseline`, `첫 단추`, `no-op wrapper` 같은 표현이 작업을 안전하게 시작하는 말처럼 쓰였다. 이후 검토에서는 이 표현들이 product surface 이후에 쓰이면 유효할 수 있지만, surface 이후 첫 구현 대상을 정하기 전에 나오면 provider나 helper 쪽으로 작업을 당길 수 있다는 점이 드러났다.

이 보정은 작업량을 늘리자는 뜻이 아니라, 이미 펼친 구현면을 문서 구조나 wrapper 아래로 다시 접지 않고 product path에서 실제 leaf fact를 먼저 만들게 하자는 기준이다.

`top-down 요소`라는 표현도 검토 과정에서 조정됐다. 문제는 top-down 자체가 아니라, 상위 spec 제목, 첫 AC, next slice, 하위 spec 번호 같은 앵커가 product surface가 아니라 구현 객체처럼 읽힐 때였다. 이때 작업은 상위 앵커 아래를 depth-first로 채우는 방향으로 기울 수 있다.

따라서 마지막에 남은 실행 감각은 `Surface first, product leaf producer first, top-level adapter last`에 가까웠다. 이 문장은 새 원칙을 더 쌓는 문장이라기보다, 구현면을 펼친 뒤 첫 구현 대상이 어디에 있어야 하는지 가리키는 ordering rule로 정리됐다.

## 확인된 사실과 해석

기존 active spec에는 `LangSmith no-op 안전 wrapper -> material upload trace -> question 실행 config/prompt snapshot -> /api/questions trace` 순서가 있었고, 이는 다음 작업을 wrapper-first로 회수하게 만들 수 있었다.

Implementation Surface 테이블은 이미 material ingest observation, runtime config snapshot, prompt snapshot, question path observation, LangSmith export를 가로로 펼치고 있었다. 문제는 surface가 없는 것이 아니라, surface 이후 첫 구현 대상이 product fact producer가 아니라 상위 wrapper/provider 쪽으로 기울 수 있다는 점이었다.

이번 보정은 다음 순서로 좁혀졌다.

```text
Implementation Surface
-> product path의 leaf producer
-> endpoint/domain에 연결된 record 생성
-> 테스트나 contract로 확인
-> adapter/provider/export가 record를 소비
```

`leaf producer`는 low-level utility가 아니라 product path에서 실제 fact를 만드는 producer다. 예를 들면 `/api/materials` upload event가 material id, parse status, source unit count, failure kind를 record로 남기는 것이다.

## 기각·보류된 후보

기각한 방향:

- "좁히지 말라", "product surface를 보라" 같은 원칙을 더 반복하는 것.
- LangSmith adapter, no-op wrapper, trace provider interface를 첫 구현 단위로 두는 것.
- `bottom-up first`를 helper, type, schema, event bus 같은 plumbing부터 만들라는 뜻으로 쓰는 것.
- 문서 번호나 하위 spec 순서를 그대로 구현 순서로 승격하는 것.

보류한 방향:

- `docs/specs/README.md`에 같은 원칙을 즉시 추가하는 것. 구현면 펼치기 원칙은 이미 있고, 이번에는 surface 이후 실행 순서 보정이 더 직접적인 문제였다.
- 전역 지침이나 글로벌 skill로 확장하는 것. 현재 관찰은 TripProof의 spec-driven 운영에서 나온 repo-local calibration에 가깝다.

## 재진입 메모

비슷한 상황에서 다음 질문을 먼저 본다.

```text
Surface는 이미 펼쳐져 있는가?
첫 구현 대상은 product path의 leaf producer인가?
그 leaf는 어떤 endpoint/domain에서 어떤 product fact를 만드는가?
상위 adapter가 소비할 product payload가 이미 있는가?
```

이 질문은 승인 gate가 아니라, surface 이후 첫 구현 대상이 wrapper/provider/plumbing으로 기울지 확인하는 짧은 점검이다.
