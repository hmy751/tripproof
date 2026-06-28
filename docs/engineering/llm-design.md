# LLM 설계

LLM을 제품 동작의 한 부품으로 넣을 때 어디까지 맡기고 어디서 코드로 잡을지에 대한 기준이다. 규칙표가 아니라 설계가 헷갈릴 때 꺼내 보는 lens다.

## 관통 기준: 비결정성은 양날이다

보통 코드는 같은 입력에 같은 출력을 준다 — 통제 가능하지만 그만큼 경직돼 있다. LLM은 입력→출력을 고정하지 못한다. 그 통제 불가능성은 결함이 아니라 **종합·연결·후보 생성**이라는 능력과 같은 성질의 양면이다. 불확실성만 도려내려 하면 종합 능력도 같이 죽는다.

그래서 LLM은 발산이 값인 자리에 두고, 제품 사실로 확정되는 경계는 코드 계약으로 좁힌다. 단, 단계·검증기·라우팅을 늘리기 전에 더 단순한 해법(단일 호출 + 검색 + 예시, 코드 규칙)으로 충분하지 않은지 먼저 본다. **복잡도는 측정으로 개선이 보일 때만 더한다** — 단계·검증기를 더할 때 정확도뿐 아니라 비용·latency도 같은 저울에 올린다.

## 어디에·얼마나 LLM을 둘까

LLM을 넣기 전에 두 가지를 본다 — 이 일이 LLM에 맞는가, 틀리면 얼마나 위험한가.

- **적합도**: 입력이 비정형(문서·대화·이메일)이고, 정확한 규칙보다 의미·맥락이 중요하며, 예외가 많아 규칙으로 유지하기 어렵거나, 밟을 단계·순서를 미리 모를수록 LLM에 맞다. 입력과 규칙이 분명하면 일반 코드가 낫다.
- **위험**: 틀렸을 때 되돌리기 어렵거나(돈·데이터·예약 변경), 권한이 넓거나, 보안·규제에 닿을수록 직접 실행을 맡기지 않는다.

둘을 곱해 보면 자리가 정해진다. 적합도가 낮으면 일반 코드다. 적합도가 높고 위험이 낮으면 LLM이 직접 하되 검증을 붙이고, 위험이 높으면 LLM은 후보만 내고 확정·실행은 코드나 사람이 막는다(제안 → 승인 → 실행).

LLM이 필요해도 가장 단순한 데서 시작해 한 칸씩만 올린다(위 관통 기준).

1. **단일 호출** — 한 번에 끝나는 일(요약·분류·추출). 답에 외부 지식이 필요하면 검색을 붙인다(RAG). 대부분의 자료 QA가 여기다.
2. **정해진 워크플로** — 단계가 미리 정해져 있으면 여러 호출을 코드가 잇는다(prompt chaining·routing·parallelization·evaluator-optimizer). 경로를 코드가 정하므로 예측 가능하다.
3. **에이전트 + tools** — 현재 값을 조회하거나 외부에 행동해야 하면 도구를 부르고(tool calling), 도구를 몇 번·어떤 순서로 쓸지 미리 모르면 LLM이 관찰하며 정한다(agent).
4. **멀티에이전트** — 한 에이전트가 도구·책임·보안 경계를 감당 못 할 때만. 조율 비용·지연·실패 지점이 같이 는다.

도구·에이전트를 붙일 땐 프롬프트보다 **계약을 먼저** 정한다 — 입력, 구조화 출력, 도구 목록과 권한, 최대 반복, 실패 fallback, 사람 승인 지점, 평가 가능한 성공 조건.

LLM은 틀린다는 전제로 사용자 쪽도 설계한다(Defensive UX). 안 틀리게 만드는 것만이 아니라, 틀려도 사용자가 알아채고 고치게 둔다 — 근거를 함께 보이고, 불확실하면 그렇게 표시하며(아래 불확실성 라우팅), 위험한 확정은 사람 검토로 보낸다.

## 책임 분리

LLM에게 맡길 일과 코드가 쥘 일을 섞지 않는다.

LLM에게 맡길 일:
- 질문 의도와 숨은 요구를 해석한다.
- 표현이 다른 근거를 연결하고, 조건·예외·반례를 종합한다.
- 후보 답변·claim·근거·불확실한 지점을 만든다.
- 여러 근거를 사람이 읽을 설명으로 압축한다.

코드·제품 계약이 쥘 일:
- 어떤 값이 확정 상태로 올라가는지 정한다.
- `supported`/`needs_review`/`missing`이 사용자에게 어떤 약속인지 정한다.
- 근거(source provenance)가 실제로 존재하는지 보장한다.
- 출력이 강등·보류·재검색·재질문·사람 검토 중 어디로 가는지 라우팅한다.
- 실패를 관측 가능한 record와 eval 축으로 남긴다.

한 LLM 호출이 답변·상태 확정·근거 선택을 동시에 하면, 자기가 만든 답을 자기가 맞다고 인증하는 꼴이 된다(self-certifying). 그러면 가장 어려운 질문 — "이 근거가 이 주장을 정당화하나" — 이 모델의 자기선언에 묻힌다.

## 입력: 무엇을 보고 종합할지 겨냥한다

- LLM의 출력을 좁히는 대신 **입력을 깎아** 종합을 겨냥한다. 검색으로 후보를 먼저 뽑아 주는 것이 이 자리다(RAG).
- 후보에 의미 구분(이건 정책·조건·요청)이 붙어 있으면 그 표시를 **프롬프트까지 실어** 보낸다 — 모아 놓고 직렬화에서 떨구면 없는 것과 같다.
- 배치·순서도 신호다 — 조건·예외 근거가 긴 맥락 중간에 묻히면 모델이 실질적으로 못 본다(lost in the middle).
- 출력 스키마도 입력 설계다. `body`(완성 문장)부터 받으려는 순간이면 유창한 문장이 판단 중심이 된다. claim·지지 근거·조건·부족한 것을 먼저 받고, 답변문은 그 관계를 풀어 쓴 결과로 둔다(답 먼저가 아니라 관계 먼저, relation-first).
- 후보가 없으면 넓은 문서 전체를 LLM에 넘겨 답을 기대하지 않는다. 그건 겨냥을 포기하고 떠넘기는 것이다.

예: 답변 합성 프롬프트를 만드는 `_format_source_blocks`(library_chat.py)는 `source_unit_id·locator·text`만 직렬화하고 source unit의 `metadata`를 통째로 버린다. 같은 `kind`(policy·request_note 등)는 retrieval을 거쳐 관측 record까지 살아오는데(observation.py) LLM 입력에서만 떨어진다 — 분류가 죽는 게 아니라 프롬프트 직렬화 한 곳에서만 죽어, 모델은 조건 문장과 값 문장을 구분할 단서를 못 받는다.

## 출력: 정당화를 생성과 분리해 검증한다

- 답을 만든 주체가 자기 답의 상태(`supported` 등)까지 확정하게 두지 않는다. **생성과 검증은 다른 단계다.** LLM이 답·값·상태·근거(`body`·`value`·`evidence_state`·`source_unit_id`·`evidence_snippet`)를 한 호출에 다 내고 코드가 그 상태를 그대로 받으면, 자기검증에 기댄 것이다. 같은 호출·같은 모델이 생성과 검증을 겸하면, 검증이 생성의 편향을 그대로 물려받는다.
- 검증의 기준은 "근거가 있음"이 아니라 **"근거가 주장을 정당화함(entailment)"** 이다. 인용 문구가 원문에 있는지(citation existence)와 그 인용이 주장을 떠받치는지는 다르다. structured output(strict)은 모양을 보장하지 `evidence_state`의 정당성을 보장하지 않는다.
- 상태는 prompt가 보장하지 못한다. "조건을 고려하라"를 프롬프트에 더해도 LLM이 놓치면 같은 실패가 반복된다 — "조건 근거가 없으면 `supported`가 못 된다"는 코드 계약이라야 보장된다. prompt만 늘고 계약이 그대로면 같은 자기선언을 더 복잡한 말로 받는 것이다.
- 별도 검증을 둬도 그 검증기가 약하면 confident-wrong을 못 거른다. 검증기 자체도 eval 대상이다 — 입력·근거·판정을 직접 읽어 사람 판단과 보정한다. 분리가 곧 신뢰는 아니다.
- 검증기·근거선택기의 판정은 후보가 어떤 순서·길이로 들어왔는지(position bias), 그리고 자기가 낸 답인지(self-enhancement bias)에 흔들린다. 같은 입력을 순서만 바꿔 돌려 결과가 같을 때만 믿는다. 검증 호출은 temperature 0으로 두거나, 아예 코드로 entailment를 따져 결정성을 확보한다.

예: 답이 "확정된 조건입니다"인데 근거로 댄 건 "NonSmoke,LargeBed"뿐이면, 그 문구는 원문에 있어도 "확정"을 뒷받침하지 않는다. grounding(`_ground_snippet`, evidence.py)은 snippet이 원문에 있는지만 보고 entailment는 안 봐서 코드는 이걸 supported로 통과시킨다. 그나마 있는 강등 게이트(`_supported_value_matches_question`)도 시간 질문에만 답 모양을 보고 나머지는 통과시킨다 — 주석이 "MISSING은 실제 grounding 실패와 구분되지 않는다"고 자인한다.

설계 패턴: 답을 만든 모델과 별개 검사(코드 entailment, 별도 스크리닝 모델, 외부 정답)가 LLM 바깥에서 상태를 판정한다. 이 제품에선 한 번의 강등 게이트를 기본으로 두고, 반복 평가-수정 루프(evaluator-optimizer)는 그 반복이 측정 가능한 가치를 줄 때만 더한다.

## 불확실성 라우팅

`needs_review`는 실패나 빈 근거가 아니라 정상 상태다. 불확실성의 종류마다 목적지가 다르다.

- 근거는 있으나 확정성이 낮다 → `needs_review`
- 값은 있으나 조건 문맥이 부족하다 → 추가 retrieval
- 질문이 모호하다 → 되묻기(clarification)
- 근거가 주장을 받치지 못한다 → `missing` 또는 답변 재작성
- 위험이 큰 확정이다 → 사람 검토 보류
- 같은 항목에 자료가 다른 값을 말한다 → `conflict`로 양쪽 후보 보존(상태 정의는 `product-model.md`)

전부 `missing`으로 낮추면 좋은 후보까지 사라지고, 전부 `supported`로 올리면 자신있는 오답이 생긴다.

## 측정: 실패를 보이게 만든다

- 무엇이 틀렸는지 **측정이 없으면 포인트를 못 잡는다.** 고치기 전에 실패 trace를 직접 보고 유형을 분류한다(error analysis). 데이터를 보는 마찰을 없앤다.
- 채점이 보상하는 것이 곧 모델·시스템이 통과 전략으로 배우는 것이다. "모름 인정"을 벌하고 "자신있는 찍기"를 보상하면 confident-wrong이 남는다. 검증·스코어보드가 **근거 부족한 `supported`(자신있는 오답)를 모르는 답과 구분**해 드러내게 한다.
- 실패 원인을 엉뚱한 컴포넌트에 귀속하지 않는다. retrieval / 맥락 구성 / LLM 해석 / certification(상태 게이트) / 표시 변환 중 어디서 났는지 가른다. 이 축은 관측 trace와 맞물려 있다 — `SourceRetrievalTrace`와 observation step tree(`source_retrieval`·`context_assembly`·`composer_call`)가 검색 측과 생성 측을 갈라 준다. 다만 5축 중 certification·표시 변환은 아직 step으로 안 찍혀서, 정작 이 제품의 실제 버그가 난 certification 층(코드가 존재만 검사한 자리)이 trace에서 가장 안 보인다.

- "근거가 틀렸다"며 검색만 계속 고치는데 그 변경이 도움이 되는지 말할 측정이 없으면, 증상을 쫓는 중이다.
- 형식·단위 테스트 통과를 제품 동작 통과로 말하지 않는다(`testing.md`). citation 일치율 같은 generic 지표 하나로 품질을 말하면, 그 지표가 못 보는 실패가 그대로 통과한다.

예: 지금 이 제품의 질문셋을 측정하면 깨끗이 통과하는 건 날짜 같은 field lookup뿐이고, 종합이 필요한 질문은 confident-wrong("확정"이 아닌 걸 "확정"으로)이거나 miss다 — 취소·추가비용 질문은 같은 입력에도 run마다 `supported`↔`missing`으로 뒤집힌다. 그래서 위 관통 기준의 양날 중 좋은쪽(종합·연결이 값이 된 자리)은 이 제품에선 아직 grounded되지 않았다 — 능력·원리로만 있다.

## 자신있다고 맞는 게 아니다

- 답이 얼마나 자신있고 매끄러운지는 정답의 신호가 아니다. LLM은 정답보다 그럴듯하고 사용자 기대에 맞는 답으로 기운다(sycophancy). 사람도 확신에 찬 틀린 설명에 과의존한다.
- 그래서 코드가 신뢰할 신호를 "문장의 자신감"이 아니라 외부 근거(entailment)와 측정에 둔다.
- 위험이 큰 자료(예: 여행 예약 확인)에서는 **자신있는 오답이 모르는 답보다 더 위험하다.** `supported`를 늘리는 것보다 근거 부족한 `supported`를 줄이는 것을 우선한다.

## 판단 질문

LLM이 들어간 변경 전에 던진다.

- 지금 LLM에 맡긴 게 의미 해석인가, 제품 상태 확정인가?
- 이 출력은 후보인가, 사용자에게 약속할 사실인가?
- citation 존재와 claim support를 분리했나?
- 불확실한 경우가 `needs_review`·되묻기·재검색·사람 검토로 갈 수 있나?
- eval이 이 변경을 retrieval/해석/certification 어디 개선인지 보여주나?
- 이 실패를 prompt 문구로만 막으려 하고 있지 않나? 더 단순한 해법으로 충분하지 않나?

## 근거 자료

링크는 재접근 경로다. 판단의 핵심은 위 본문에 옮겨 두었다. (공식 가이드 URL은 2026-06 접근 기준이며 도메인이 옮겨갈 수 있다.)

LLM의 성질·실패 모드:
- Language Models (Mostly) Know What They Know — Anthropic, 2022. https://arxiv.org/abs/2207.05221 — 자기평가(P(True))는 분리된 단계로는 부분적으로 작동하나 새 task에서 보정이 무너진다.
- Large Language Models Cannot Self-Correct Reasoning Yet — Huang et al., 2023. https://arxiv.org/abs/2310.01798 — 외부 피드백 없는 자기교정은 신뢰하기 어렵고 때로 역효과.
- Towards Understanding Sycophancy in Language Models — Anthropic, 2023. https://arxiv.org/abs/2310.13548 — 설득력 있는 영합적 답이 정답보다 선호되기도 한다.
- Why Language Models Hallucinate — Kalai et al., 2025. https://arxiv.org/abs/2509.04664 — 불확실성 인정을 벌하고 찍기를 보상하는 채점이 confident-wrong을 남긴다.

근거 존재 ≠ 근거가 정당화함:
- Measuring Attribution in NLG (AIS) — Rashkin et al., 2021. https://arxiv.org/abs/2112.12870 — source가 진술을 뒷받침하는지를 독립 기준으로 형식화.
- Enabling LLMs to Generate Text with Citations (ALCE) — Gao et al., EMNLP 2023. https://aclanthology.org/2023.emnlp-main.398/ — 인용이 주장을 entail하는지로 인용 품질을 측정.
- Correctness is not Faithfulness in RAG Attributions — Wallat et al., 2024. https://arxiv.org/abs/2412.18004 — 인용의 상당수가 사후합리화, 존재만으론 불충분.
- RAGAS — Es et al., 2023. https://arxiv.org/abs/2309.15217 · https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ — 답을 claim 단위로 쪼개 context가 뒷받침하는 비율로 측정.

입력·context 설계:
- Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023. https://arxiv.org/abs/2307.03172 — 관련 정보가 긴 맥락 중간에 있으면 성능이 떨어진다(U자형). 배치·순서도 신호다.
- Effective context engineering for AI agents — Anthropic, 2025. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents — 추론에 필요한 최소 고신호 토큰만; context는 한정 자원.

생성/검증 분리:
- Building Effective Agents — Anthropic, 2024. https://www.anthropic.com/research/building-effective-agents — 별도 모델로 스크리닝하는 가드레일; 복잡도는 결과가 개선될 때만.
- Judging LLM-as-a-Judge (MT-Bench) — Zheng et al., 2023. https://arxiv.org/abs/2306.05685 — judge의 self-enhancement bias; 일치율 높다고 정확도 높은 건 아니다.
- Who Validates the Validators? — Shankar et al., UIST 2024. https://arxiv.org/abs/2404.12272 — LLM 평가기는 평가 대상의 결함을 상속한다.
- The Dual LLM pattern — Willison, 2023. https://simonwillison.net/2023/Apr/25/dual-llm-pattern/ — 한 LLM 출력을 다른 주체가 맹신 말고 구조로 분리.

계약·검증 (벤더 공식 가이드):
- Reduce hallucinations — Anthropic. https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations — 주장마다 인용을 찾게 하고 못 찾으면 철회; "모른다" 권한을 준다.
- Structured Outputs — Anthropic. https://platform.claude.com/docs/en/build-with-claude/structured-outputs — constrained decoding으로 schema·type만 보장; 값의 사실성은 보장하지 않는다.
- Structured Outputs — OpenAI. https://developers.openai.com/api/docs/guides/structured-outputs — 같은 한계: 스키마는 보장하나 값의 사실성은 보장하지 않는다.
- Function calling — OpenAI. https://developers.openai.com/api/docs/guides/function-calling — 모델은 제안할 뿐, 실행·판단은 application code가 소유한다.
- Guardrails and human review — OpenAI. https://developers.openai.com/api/docs/guides/agents/guardrails-approvals — output guardrail은 생성과 분리된 검증 레이어; 불확실·민감 케이스는 사람 검토로 라우팅한다.

eval·측정:
- Your AI Product Needs Evals · A Field Guide to Rapidly Improving AI Products — Husain, 2024–2025. https://hamel.dev/blog/posts/evals/ · https://hamel.dev/blog/posts/field-guide/ — error analysis가 최고 ROI; 측정 없이 고치면 도움 여부를 말할 수 없다.
- Demystifying evals for AI agents — Anthropic, 2026. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents — 실패에서 뽑은 소수 사례로 시작; judge는 트랜스크립트를 직접 읽어 사람과 보정한다.
- Graders — OpenAI. https://developers.openai.com/api/docs/guides/graders — grader는 사람 라벨과 보정한 뒤 쓰고, grader hacking을 경계한다.
- Common pitfalls when building generative AI — Huyen, 2025. https://huyenchip.com/2025/01/16/ai-engineering-pitfalls.html — AI 채점자는 결정론적이지 않다.
