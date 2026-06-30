# Raw Notes - LLM 답변 자기-인증 실패 귀속 재정의

이 파일은 `index.md` 결정의 배경 재료이며, 이 귀속에 이른 디버깅 여정과 거쳐온 오진을 보존하기 위한 자료다. 현재 실행 기준이나 작업 대기열이 아니다. 결론은 `index.md`에 있고, 여기 후보·표현을 현재 작업으로 쓰려면 `index.md`와 현재 코드 상태로 다시 판단한다. 원본 대화 전체는 공개 repo 밖 개인 raw 기록으로 따로 보존돼 있고, 아래 발췌가 판단을 독립적으로 담는다.

## 왜 raw가 필요한가

이 결정의 가치는 "answer validation이 필요하다"는 결론보다, **거기에 도달하기까지 실패 지점을 세 번 잘못 짚었다는 과정**에 있다. 같은 증상(틀린 supported)을 두고 처음엔 retrieval, 다음엔 grounding, 다음엔 sufficiency로 원인을 미뤘다. 이 미끄러짐의 모양을 남겨야, 다음에 비슷한 confident-wrong을 만났을 때 "근거를 더 잘 찾자 / 근거 검사를 더 하자"는 익숙한 출발점으로 돌아가 같은 한 바퀴를 다시 돌지 않는다. 포트폴리오·면접 자료로 꺼낼 때도 핵심은 버그 자체가 아니라 이 **오진→재귀속**의 진단 감각이다.

## 대화·조사에서 드러난 문제 감각

### 출발: supported가 어떻게 정해지는지 묻는 데서 시작했다

- 질문은 단순했다 — "supported/missing은 어느 단계에서, 무엇을 보고 정해지나?"
- 첫 설명은 흐름을 이렇게 잡았다: retrieval 후보 → LLM이 item별 `evidence_state` 반환 → 코드가 grounding 검증 → 최종 상태. 그리고 실패를 "grounding이 값의 존재만 보고 충분성(sufficiency)은 못 본다"로 정리했다.
- 이 정리는 일관돼 보였지만 실패 지점을 검증 단계로 미루고 있었다.

### 1차 교정: "통과"라는 말을 두 뜻으로 섞었다

- "grounding이 너무 좁은 일만 한다"는 진단과 "같은 케이스에서 grounding도 supported도 둘 다 통과한다"는 관찰이 충돌했다 — 표면적으로는 모순이다.
- 정정: grounding은 **맡은 범위에선 정상 작동**한다. 문제는 grounding 통과를 supported 충분으로 취급한 product 계약이 약한 것이다. 즉 "grounding이 오작동"이 아니라 "supported의 의미가 과하게 넓다."

### 2차 교정 — 전환점: "body가 이미 틀렸다"

- 데이터 형태를 비유 없이 끝까지 펼친 뒤(질문 → LLM payload → API response → eval run.json), 정작 가장 앞이 드러났다. 귀속이 한 단계 앞으로 이동했다 — 핵심은 검증이 아니라 **첫 LLM 답변(`body`)이 생성 단계에서 이미 틀렸다는 것**이고, 뒷단에서 근거 존재만 반복 확인해도 틀린 답은 그대로 통과한다.
- 이게 이 케이스의 전환점이다. 틀린 자리는 `body`("확정된 조건입니다")와 `value`("확정")이고, 근거 `"NonSmoke,LargeBed"`에는 "확정"이 없다. 생성에서 이미 틀렸는데, 검증은 "snippet이 원문에 있나"만 물어 yes로 통과시켰다.

### 3차 교정 — 구조 통찰: 앞단 단순 / 뒷단 복잡, 그런데 뒤가 얇았다

- 단순 채팅으로 환원하면 앞단(근거 후보 뽑고 조립)은 단순 행동, 뒷단(답이 근거로 정당화되는지 판단)이 복잡한 행동이다. 그런데 이 제품은 카드형(필드) 자료 구조에 답변 흐름을 끼워 맞추다 경계가 꼬여, 뒷단이 citation 존재 검사로 얇아져 있었다.
- 그래서 검색·근거만 반복해서 고치는 방향은 구조 원인(self-certification)을 놓친 채 같은 component만 재수정하게 만든다 — 증상을 따라가며 같은 자리를 다시 고치는 셈이다.
- 한 호출이 답변·상태 인증·근거 선택을 동시에 하는 self-certification이 핵심 구조 결함이다. 가장 어려운 판단(entailment)이 LLM 자기선언으로 묻힌다.

### 필요한 전문성 — 구현자보다 판단 보조 관점부터

코드를 고치기 전에 "누가 필요한가"를 먼저 좁혔다. 도메인(호텔/Agoda) 전문가는 1순위가 아니었다 — 흔들리는 건 특정 지식이 아니라 답변 생성 구조 자체였다.

- RAG/LLM answer pipeline: LLM이 어디까지 판단하고 어디부터 코드가 검증하나(후보 → 검증 → final 경계 재정의).
- answer/data contract: `body`·`value`·`evidence_state`·`evidence`가 각각 무슨 책임인가. 카드 데이터와 사용자 답변을 분리할 가능성.
- evaluation: 현재 eval은 `evidence_state_counts`·cue substring 중심이라 body/value 의미 오류를 약하게 잡는다. body가 cited evidence에서 entail되는지를 관찰하는 축이 필요(단, semantic judge부터 넣자는 뜻은 아님 — 실패 taxonomy가 먼저).
- product/UX safety: 여행 예약에서 "확정" 같은 단어의 위험. 상태-문구 안전 기준.

## 출처와 확인된 사실

- 데이터 흐름과 실패 지점은 실제 코드·observation으로 확인했다.
  - 조건 문맥(`request_note`)은 P1-01 retrieval 후보에 이미 있었다 → "데이터 부재"가 아니다.
  - `_format_source_blocks`는 프롬프트에 `metadata`를 안 싣고, `_ground_snippet`은 substring만 보며, 강등 게이트는 시간 질문에만 답 모양을 본다 → certification 층이 얇다.
  - 최종 `missing`은 "LLM이 missing이라 함"과 "supported였다가 강등됨"이 같은 모양으로 들어와 원인이 안 보인다.
- 이 디버깅 이후의 문서 작업: 이 판단 감각을 `docs/engineering/llm-design.md`(LLM 설계 lens)로 일반화했고, 이후 lens의 입력·출력·측정 예시를 위 실제 함수들에 grounding하고, 현재 질문셋의 통과/실패 양상(field lookup만 통과, 종합 질문은 confident-wrong 또는 run간 뒤집힘)을 측정 한계로 명시했다. lens 문서의 신설 근거 자체는 `2026-06-22-engineering-principle-docs` 결정이 소유한다.

## 기각·보류된 후보 (현재 후보 아님)

- 실패를 retrieval recall 문제로 귀속 — 기각(근거는 후보에 있었다).
- 실패를 grounding 버그로 귀속 — 기각(grounding은 맡은 범위에선 정상; supported 계약이 약했다).
- "sufficiency gate"라는 이름으로만 04를 정의 — 보류(맞지만 부족하다. 더 정확히는 answer candidate validation이다).
- 특정 문자열·Agoda 전용 처리 — 기각.
- prompt 보강으로 우선 막기 — 보류(상태는 prompt가 아니라 코드 계약이 보장).

## 남은 불확실성

- entailment 검증을 코드 규칙으로 할지 별도 모델로 할지, gate를 어디 둘지는 미정.
- carded data(필드형)와 사용자 답변을 데이터 모델에서 분리할지 여부는 더 본다.
- conflict 상태를 1급으로 라우팅하는 작업의 우선순위는 roadmap에서 다시 판단.

## 재진입 메모

- 다음에 confident-wrong(틀린 supported)을 만나면, 검색·근거 검사부터 고치기 전에 먼저 "생성된 답변 후보 자체가 근거로 정당화되나"를 본다. 이 한 질문이 이번에 세 바퀴를 줄여줬을 자리다.
- 구현 방향과 슬라이스는 `index.md` 결정과 roadmap을 기준으로 다시 잡는다. 이 raw의 표현을 그대로 명령으로 승격하지 않는다.
