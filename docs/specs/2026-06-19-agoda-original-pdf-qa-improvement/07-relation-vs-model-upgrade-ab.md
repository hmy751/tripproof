# Relation 층 vs 모델 업그레이드 A/B

작성일: 2026-06-29 (측정·결정 반영 2026-06-30)

상태: 측정 완료. **결정: 답변 호출과 분리된 별도 relation/caveat 호출은 제거한다(방향 B).** 단 이 결정의 근거는 깨끗한 단일 변수 비교가 아니라 confounded A/B + 계측 재실행이고, 정작 이 층이 존재한 이유였던 안전망(값이 자료에 적혀 있으나 보장은 아닌 경우를 잡는 것)은 **두 안 어디서도 해결되지 않았다.** 그 문제는 `08`(body 합성)·`05`(retrieval coverage)로 이월한다.

## 왜 지금

`06`에서 막힌 지점은 프롬프트·순서 트릭이 아니라 **모델이 "이 조건이 이 값을 좌우하나"를 정밀히 못 가르는 정밀도 천장**이었다(`docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`). 약한 모델(gemma3:4b)에서 무관한 조건을 과잉 부착했고, per-unit·순서불변 변형으로도 못 잡아 되돌렸다. 그래서 다음 레버는 모델 쪽인데, 두 갈래가 있고 어느 쪽이 나은지는 측정으로만 안다.

핵심 질문: **강한 모델이 생기면 분리 relation 층이 그 추가 복잡도를 정당화하는가, 아니면 강한 답변 모델 단독이면 충분한가.** (`docs/engineering/llm-design.md`: "복잡도는 측정으로 개선이 보일 때만 더한다.")

관련 판단:

- `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/06-evidence-relation-extraction.md`
- `docs/specs/2026-06-19-agoda-original-pdf-qa-improvement/08-answer-body-synthesis-layer.md`
- `docs/implementation-notes/2026-06-29-caveat-relation-pass-overfire/`
- `docs/decisions/2026-06-25-llm-answer-self-certification-reframe/`
- `docs/engineering/llm-design.md`

## 두 갈래 (A/B)와, 비교를 흐리는 두 가지

- **A — 분리 relation 층 유지 + 강한 검출 모델**: 답변은 gemma3:4b가 쓰고, 조건(caveat) 검출만 별도 호출로 qwen3:14b가 돌린다. "분리 구조 + 좋은 검출기."
- **B — 분리 층 제거 + 답변 모델 단독 업그레이드**: 별도 호출을 빼고, 답변 모델 자체를 qwen3:14b로 올린다. "강한 모델 단독."

이 A/B는 한 변수만 바꾼 깨끗한 비교가 아니다. 결과를 읽을 때 반드시 같이 봐야 할 두 가지:

1. **A→B는 두 변수를 동시에 바꾼다** — 답변 모델 강약(gemma3:4b→qwen3:14b)과 분리 호출 유무(있음→없음)가 함께 움직인다. 그래서 A와 B의 차이를 "분리 층 때문"이라고 깨끗하게 귀속할 수 없다(confound).
2. **caveat의 출처가 둘이다** — 답변 프롬프트가 답변 모델에게 항상 "조건이 있으면 답변에 같이 적어 내라"고 시킨다. 즉 caveat을 만드는 1차 주체는 답변 모델 inline이고, 별도 검출 호출은 답변 모델이 그 칸을 비웠을 때만 도는 백업이다. 따라서 B가 "분리 층을 껐다"고 해도 조건 잡기 기능 자체가 사라진 게 아니라 강한 답변 모델이 inline으로 계속 한다. "분리 층 on/off" 비교가 아니다.

## 비교·결정 기준

단일 run으로 결정하지 않는다(`03` 재현성). repeat로 noise를 걷어낸 뒤 본다.

- **P1-01 안전망**: 값을 좌우하는 조건이 있을 때 표현·키워드와 무관하게 안정적으로 `needs_review`로 가는가.
- **과잉강등**: 깨끗한 lookup(날짜·위치·객실)이 불필요하게 `needs_review`/`missing`으로 내려가지 않는가.
- **비용·복잡도**: `A`는 답변 외 추가 호출과 별도 prompt/schema/timeout 관리, `B`는 더 큰 단일 모델.

결정 규칙: **`A`(분리 층)는 `B`(모델 단독)보다 정밀도가 동등 이상이면서 비용이 정당할 때만 유지**한다. 그렇지 않으면 `B`로 가고 분리 층을 접는다.

## 측정 결과

공통 조건(세 run 동일): material `fixtures/private/accommodation-checkin/agoda-fukuoka-booking-confirmation-private.pdf`, questions `eval/datasets/agoda-booking-confirmation/questions.json`, runtime `production`, retrieval `supabase` top_k 3, similarity threshold 0.0, embedding Ollama `nomic-embed-text-v2-moe`(768), seed `20260624`, temperature 0.0, repeat 3. 중간 partial run `20`~`22`는 timeout/중단 부산물이라 근거로 쓰지 않는다.

### (1) 표면 비교 — 사실상 무승부

| 안 | run 출처 | runtime 차이 | rule pass | P1-01 state |
| --- | --- | --- | --- | --- |
| A | `eval/runs/question-dataset/23-20260629T-relation-qwen14b-pairwise-A/repeat.json` | answer `gemma3:4b`, relation `qwen3:14b`(pairwise) | 1/8, 1/8, 1/8 | `needs_review` 2/3 (한 번은 노쇼로 drift) |
| B | `eval/runs/question-dataset/24-20260629T-answer-qwen14b-relation-disabled-B/repeat.json` | answer `qwen3:14b`, relation 없음 | 1/8, 2/8, 1/8 | `needs_review` 3/3 |

두 안 모두 안정적으로 통과하는 건 날짜 질문 하나뿐이고, state 일치는 양쪽 다 8문항 중 5~6. B가 미세하게 나아 보이지만 repeat마다 흔들리는 noise 수준이다(결과 파일도 "단일 pass 수는 개선 증거가 아니다"라고 명시). 더 중요한 사실: **통과를 막는 지배적 원인은 상태 판정이 아니라 답변 완성도다.** 상태를 `supported`로 옳게 맞춘 답조차 필요한 cue(예: 체크인 준비물에서 신분증·결제카드)를 다 안 담아 떨어졌다. 이 불완전함은 분리 relation 층과 무관해, A·B 양쪽에서 동일하게 막혔다. 그리고 **어떤 답변도 "하면 안 되는 거짓 주장"을 한 적이 없다** — 시스템은 환각이 아니라 under-answer가 문제다.

또한 **P1-01은 두 안 어디서도 실제로 "통과"한 적이 없다.** 잘해야 state 라벨만 맞았고, B의 `needs_review`도 상당 부분 의도된 의미 판단이 아니라 값이 원문에 글자로 없어 떨어진 grounding 부수효과(value_not_grounded)였다. "안전망이 제품으로 작동했다"고 말할 수 있는 순간은 없었다.

### (2) 계측 재실행 — A의 분리 검출기가 실제로 일했는지 직접 확인

표면 비교만으로는 A의 caveat이 답변 모델 inline에서 왔는지 별도 검출기에서 왔는지 구분되지 않았다. 그래서 caveat 출처를 관측에 남기도록 계측을 추가하고(관측 층에만, 제품 응답 body 불변) A 구성을 다시 repeat 3으로 돌렸다.

- run 출처: `eval/runs/question-dataset/25-20260630T-relation-qwen14b-pairwise-A-instrumented/repeat.json` (계측: `Certification.caveat_source`)

답변 24건(8문항 × 3repeat)의 caveat 출처:

| 출처 | 건수 |
| --- | --- |
| 별도 검출기가 돌았으나 조건 못 찾음 | 11 |
| 답변 모델이 inline으로 직접 적음 | 8 |
| 별도 검출기가 조건을 실제로 생산 | 3 |
| 조건 단계 없음 | 2 |

읽기:

- 분리 검출기는 24건 중 14건에서 실제로 실행됐다(빈손 11 + 생산 3). inline에 가로채여 일을 못 한 게 아니다.
- 그런데 grounding되는 조건을 실제로 만들어낸 건 단 3건이고, 그중 **유일하게 강등까지 간 1건이 false alarm**이었다 — 체크인 준비물 질문에서 "사진이 있는 신분증을 제시해야 한다"(준비물의 또 다른 항목)를 "예약 확정서 값을 제한하는 조건"으로 오인해, 맞는 `supported` 답을 `needs_review`로 깎았다. 나머지 2건은 답변 자체가 먼저 근거 grounding에 실패해 버려졌다.
- 정작 이번 A에서 P1-01이 올바르게 `needs_review`로 간 한 번은 **답변 모델(gemma3:4b)이 inline으로 적어 낸 조건**이 만든 것이지, 강한 분리 검출기가 아니었다.

즉 A의 핵심 가설("검출기를 강한 모델로 올리면 안전망이 좋아진다")은 **데이터에서 반대로 나왔다.** 강한 분리 검출기는 일할 기회를 충분히 받고도 거의 빈손이었고, 실효 있던 유일한 행동이 false alarm이었으며, 맞는 안전망은 약한 답변 모델의 inline 조건이 만들었다.

## 결정

**답변 호출과 분리된 별도 relation/caveat 호출을 제거한다(방향 B).** 근거:

- 표면 비교에서 A는 분리 층의 핵심 기대였던 정밀도 우위를 B 대비 보이지 못했고(결정 규칙 미충족),
- 계측 재실행은 더 직접적으로, 분리 검출기가 매 호출마다 비용을 쓰면서 거의 빈손이고 유일한 grounding 출력이 false alarm임을 보였다(net-negative),
- 실효 있는 조건 잡기는 답변 모델 inline이 하며, 그것은 분리 층이 있든 없든 일어난다.

여기서 "relation 제거"는 **답변 호출 뒤의 별도 caveat/relation 호출**을 제거한다는 뜻이다. 답변 모델이 한 호출 안에서 caveat/needs_review를 제안하고 코드 certification이 그것을 grounding 검증해 강등하는 구조는 남는다. 별도 층으로 분리해 운영할 복잡도가 이번 측정으로 정당화되지 않았다는 것이다.

## 이 결정이 닫지 않는 것 (중요)

- **안전망 문제 자체는 미해결이다.** "값이 자료에 적혀 있으나 보장은 아닌 경우를 안정적으로 `needs_review`로 보내기" — 이 원래 목표는 A도 B도 풀지 못했다. B의 P1-01 성공은 부분적으로 grounding 우연이었고, P1-01은 어느 안에서도 통과하지 못했다.
- **모델 크기로 안 넘어가는 천장이 따로 있다.** 코드 certification은 조건이 원문에 **있는지**(grounding)만 본다. 그 조건이 값을 실제로 **지배하는지**(governing)는 보지 못한다. 검증 입장에서 틀린 강등(체크인 준비물)과 맞는 강등(방 요청 조건)이 똑같이 보여 둘 다 받아들인다. 이 "있음 ≠ 지배함" 판단은 모델 몫인데, 검출 모델을 강하게 올려도 틀렸다.
- **깨끗한 단일 변수 비교(C arm)는 돌리지 않았다.** 답변 모델을 강한 것으로 고정하고 별도 호출만 켰다 껐다 하는 비교가 분리 층의 한계 가치를 정면으로 잴 유일한 방법이다. 다만 계측 재실행이 "별도 층은 inline 위에 거의 못 보탠다"를 이미 강하게 예고한다.
- 통과를 막는 실제 벽은 분리 층도 검출 모델도 아니라 (1) 답변 완성도(필요 cue 누락)와 (2) 검색이 가져온 근거를 답변이 인용하지 못해 통째로 떨어지는 것이다(취소·노쇼 정책이 원문에 또렷한데도 `missing`으로 떨어진 사례). 이는 `08`·`05`로 이어 본다.

## Acceptance Criteria

1. 완료. A·B를 같은 원문 PDF·`questions.json`·seed로 repeat eval했다(run 23·24).
2. 완료(단서 포함). P1-01 state는 A 2/3, B 3/3에서 `needs_review`였으나, 어느 안에서도 full pass는 아니었고 B의 `needs_review`는 일부 grounding 부수효과였다.
3. 완료. 깨끗한 lookup의 과잉강등/누락은 두 안 모두 남았고, A의 우위는 없었다.
4. 완료. A는 답변 외 별도 검출 호출과 prompt/schema/timeout 관리를 더한다. 계측 재실행에서 그 추가 호출이 24건 중 14건 실행되고도 net-negative였음을 직접 확인했다(run 25).
5. 완료. 단일 run이 아니라 repeat 3으로 판단했고, 출처를 흐리지 않기 위해 계측 재실행까지 추가했다.
6. 완료. 결정 결과는 별도 relation 호출 제거(방향 B)이며, 안전망 문제는 미해결로 `08`·`05`에 이월한다.

## 확인 방법

1. A·B 두 런타임 구성으로 같은 원문 PDF·`questions.json`·seed로 각각 실행한다.
2. P1-01과 깨끗한 lookup(날짜·위치·객실)을 두 안에서 나란히 본다.
3. caveat 출처(inline vs 분리 호출)를 관측에서 읽어, 분리 검출기가 실제로 무엇을 생산했는지 확인한다.
4. repeat로 변동을 걷어낸 뒤 정밀도·과잉강등·비용을 본다.
5. 결정과 그 run 출처를 본문에 남긴다(README의 eval 출처 규칙).

## 이번 slice에서 섞지 않는 범위

- 모델 파인튜닝이나 새 임베딩/리트리버 도입은 이 결정의 대상이 아니다.
- 답변 body 생성/완성도 개선은 `08`이 다룬다.
- retrieval coverage와 인용 실패는 `05`가 다룬다.
- eval 점수 threshold나 release gate를 확정하지 않는다.

## 남은 판단

- 별도 relation 호출 코드 제거의 실제 적용 시점·범위(되돌리기 비용)는 별도로 정한다. 계측(`caveat_source`)은 진단용이며, 유지할지 되돌릴지도 함께 정한다.
- 분리 층을 되살리려면, 답변 모델을 고정한 깨끗한 비교(C arm)에서 inline 대비 명확한 정밀도 이득을 보여야 한다.
- 다음 작업은 `08` body 합성/완성도와 `05` retrieval coverage 중 어느 벽을 먼저 잡을지다 — 통과를 막는 실제 원인이 그쪽이기 때문이다.
