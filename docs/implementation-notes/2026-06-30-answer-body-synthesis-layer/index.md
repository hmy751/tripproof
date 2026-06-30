# 2026-06-30 - 답변 body 합성 층(08) 구현·측정 관찰

## 폴더 구성

- `index.md`: 독립적으로 읽히는 관찰과 다음에 볼 경계.
- `raw.md`: A/B run(26·27)의 출처와 질문별 측정값·latency·P1-01 trace. run artifact가 gitignore라 핵심 수치를 여기 보존한다.

## 왜 남기나

`08`(답변 문장 body를 인증 후 확정 데이터에서 합성하는 층)을 구현하고 깨끗한 A/B로 측정했다. 다음 작업이 (1) body 경로의 실제 구조, (2) 점수로 환산하면 틀리는 A/B 해석, (3) "제대로 분리"가 멈춘 이유를 다시 파지 않도록 남긴다.

## 1. body는 세 번 만들어진다 (하나는 caveat 입력, 하나는 폴백, 하나가 최종)

답변 한 건의 body 비슷한 산출은 셋이다:

1. **답변(추출) 호출의 draft body** — 답변 LLM이 답 문장을 같이 낸다. 최종 출력엔 안 쓰인다. **단 죽은 필드가 아니다**: caveat extractor(`apps/server/answers/relation.py`)가 이 draft를 답변 문맥으로 입력에 넣는다(`body=candidate.draft_body`). caveat가 disabled여도 코드 경로는 이 필드에 의존한다.
2. **인증 직후 code template body** — `_item_from_certification`이 모든 항목에 template body를 깐다. 폴백 바닥이고 `missing`의 유일한 body다.
3. **합성 호출 body** — `supported`·`needs_review`만 합성으로 2번을 덮어쓴다. 사용자가 보는 최종.

기존 mismatch의 뿌리는 **순서**였다: `supported` body가 인증 *전*에 쓰인 draft였고 인증이 통과하면 그게 살았다. `08`은 body 생성을 인증 *후*로 옮겨 "확정된 사실로 문장을 쓴다"로 바로잡는다.

**"body 제대로 분리"(추출 프롬프트에서 body 제거)는 보류했다** — draft body가 caveat extractor의 입력이라, 프롬프트에서 빼면 (a) 추출 동작이 바뀌어 재측정이 필요하고 (b) 비활성 caveat 경로의 입력을 함께 손봐야 한다. caveat extractor의 운명(방향 B로 진짜 제거할지)을 정할 때 draft body·추출 프롬프트 body를 한 번에 들어내는 게 깨끗하다.

## 2. A/B는 점수로 환산하면 틀린다 (수치는 raw.md)

답변 모델만 변수(caveat disabled, 합성 모델 `gemma3:4b` 고정)인 깨끗한 비교:

- rule pass는 평평하지 않고 **일관된 +1**(gemma 1/8 → qwen 2/8, 3 repeat 모두).
- 그러나 **문장 완성도 향상은 점수보다 크다**. cue 채점이 부분문자열 게이트라, 옳은 답도 정답 문구 한 단어가 없으면 fail로 떨어뜨린다(P1-01 B는 state 정답 `needs_review`인데 "Remarks" 글자 없어 fail). **pass 수 = 제품 품질이 아니다.**
- **qwen 답변 모델은 ~8배 느리다**(문항당 ~47초 vs gemma ~6초, 8문항 셋 ~6.4분 vs ~50초). 명시 duration metric이 아니라 observation export 타임스탬프 간격 추론이다.
- 점수·완성도 차이는 **답변(추출) 모델 강약**에서 온다. body 합성층은 잠긴 사실을 옮길 뿐이다 — 합성 모델은 양 arm 동일(`gemma3:4b`)이었다.

## 3. P1-01: 안전망은 inline caveat + certify에서 나왔다 (방향 B 실데이터)

P1-01("NonSmoke,LargeBed는 확정인가", 기대 `needs_review`)에서 두 arm이 갈린 지점은 검색이 아니라 답변 모델이다. 조건 문장("모든 특별 요청은 체크인 시 숙소 측의 상황에 따라 반영 여부가 결정됩니다")은 두 arm 모두 같은 후보에 들어와 있었다.

- qwen(B): 조건을 답변 payload에 **inline으로** 냄(`caveat_source: inline`, 분리 검출기 disabled) → certify가 grounding 확인 → `limited_by_caveat` → `needs_review`(정답).
- gemma(A): 조건을 inline으로 못 냄 → `ungrounded` → `missing`.

→ 이 케이스의 안전망은 **별도 검출기가 아니라 답변 모델 inline + 코드 certify**에서 나왔고, `07`의 방향 B(분리 호출 제거, inline에 맡김)와 맞는 실데이터다. 단 강한 답변 모델에 기댄다 — 약한 모델은 inline이 비어 안전망이 안 선다. (trace: `raw.md`)

## 4. 남은 어정쩡한 분리와 얇은 안전망

- **answer_summary는 아직 code template**이다(`_summary_for_items`). 항목 body는 합성인데 요약 문장은 고정 template — "답 텍스트"가 반은 합성·반은 template로 갈렸다.
- **폴백이 전체 단위**다. 합성 결과에서 한 항목이라도 검증에 걸리면(id 불일치/prompt leak/`needs_review` 과잉확정) 멀쩡한 나머지까지 통째로 template로 되돌린다. 안전 방향이지만 입자가 거칠다.
- **`needs_review` 과잉확정 차단(`_looks_confirmed`)은 정확 문구 5개 blocklist**다. "무료입니다/가능합니다" 같은 변형 단정은 통과한다. 진짜 안전망은 잠긴 state(합성이 못 뒤집음)와 합성 프롬프트이고, blocklist는 거친 백스톱이다 — 키워드로 더 늘리면 프로젝트가 피하는 lexical 판정으로 흐른다.

## 5. 토글을 둔 이유

`08`은 새 LLM 층이라 비용·실패면이 생긴다. 그런데 끄는 길이 없으면 "합성 vs template만"을 못 잰다. `TRIPPROOF_BODY_SYNTHESIS_ENABLED`로 끄면 template body만 쓰고 runtime snapshot에 `enabled:false`로 기록한다 — 합성층이 밋밋한 template 대비 무엇을 버는지 단일 변수로 재기 위한 게이트다.

## 다음에 볼 것

- 모델 선택(완성도 vs ~8배 latency)은 미결 — 점수 이득이 작아 product 기본은 작은 모델이 합리적 휴식점일 수 있다.
- caveat extractor의 운명을 정할 때 draft body·추출 프롬프트 body를 함께 정리한다.
- 폴백 입자(전체 vs 항목)와 `_looks_confirmed` 확장 여부는 안전망 두께 결정과 함께 본다.
- 단위 테스트는 `body`만 교체(state 불변)·missing template·합성 비활성 폴백을 고정하나, 적대적 폴백(id 불일치·중복·prompt leak)과 `needs_review` 과잉확정 폴백의 직접 커버는 아직 얇다.
