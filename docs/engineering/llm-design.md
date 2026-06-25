# LLM 설계

LLM을 제품 동작의 한 부품으로 둘 때의 경계 판단이다. `principle.md`가 코드 일반, `testing.md`가 검증, `ai-coding.md`가 AI에게 코드를 맡길 때라면, 여기선 LLM 자체를 흐름 안에 넣을 때 어디까지 맡기고 어디서 한정할지를 둔다.

## 관통 기준: 비결정성은 양날이다

보통 코드는 같은 입력에 같은 출력을 준다 — 통제 가능하지만 그만큼 경직돼 있다. LLM은 입력→출력을 고정하지 못한다. 그 통제 불가능성은 결함이 아니라 **종합·연결·후보 생성**이라는 능력과 같은 성질의 양면이다. 불확실성만 도려내려 하면 종합 능력도 같이 죽는다.

그래서 설계는 "LLM을 믿을 만하게 만들기"도 "불신해 가두기"도 아니다. **발산이 값인 자리에 LLM을 두고, 그 주위의 이음매(seam)를 설계한다.** 통제는 이음매에, 자유는 가운데.

- LLM이 비결정적이라는 이유로 출력을 더 좁은 형식으로만 조이고 있으면, 능력 쪽 날을 같이 깎는 것이다.
- 반대로 LLM 출력을 그대로 최종 계약으로 받고 있으면, 이음매를 안 둔 것이다.

이음매는 셋이다 — 입력(무엇을 보고 종합할지), 출력(정당화를 분리 검증), 측정(실패를 보이게). 그리고 셋을 가로지르는 한 줄: 유창함은 정확도의 신호가 아니다.

## 가운데는 자유: LLM에게 맡길 것

- 흐릿하고 열린 자료를 가로질러 **종합·연결·후보 생성**하는 일. LLM이 가장 잘하고 보통 코드가 못 하는 영역이다.
- 답의 초안, 후보 근거 제안, 분류, 요약처럼 발산이 값인 일.
- 이 일을 규칙·정규식으로 되돌리려 하고 있으면 강점을 버리는 것이다. 가두는 대신 아래 이음매로 한정한다.

## 입력 이음매: 무엇을 보고 종합할지 겨냥한다

- LLM의 출력을 좁히는 대신 **입력을 깎아** 종합을 겨냥한다. 검색으로 후보를 먼저 뽑아 주는 것이 이 자리다(RAG).
- 후보에 의미 구분(이건 정책·조건·요청)이 붙어 있으면 그 표시를 **프롬프트까지 실어** 보낸다. retrieval까지 살아온 메타데이터를 프롬프트 직렬화에서 떨구면, 좋은 재료를 모아 놓고 안 보여 주는 것이다.
- 후보가 없으면 넓은 문서 전체를 LLM에 넘겨 답을 기대하지 않는다. 그건 겨냥을 포기하고 가운데에 떠넘기는 것이다.

예: 답변 합성에서 source unit의 `kind`(policy·request_note 등)가 retrieval까지 보존되는데 프롬프트엔 `text`만 직렬화되면, LLM은 조건 문장과 값 문장을 구분할 단서를 못 받는다 — 입력 이음매가 새는 자리다.

## 출력 이음매: 정당화를 생성과 분리해 검증한다

- 답을 만든 주체가 자기 답의 상태(supported 등)까지 확정하게 두지 않는다. **생성과 검증은 다른 단계다.** 같은 호출·같은 모델이 둘을 겸하면 검증이 생성의 편향을 상속한다.
- 검증의 기준은 "근거가 있음"이 아니라 **"근거가 주장을 정당화함(entailment)"** 이다. 인용 문자열이 원문에 존재하는지(citation existence)와, 그 인용이 주장을 함의하는지(entailment·faithfulness)는 다르다.
- 별도 검증을 둬도 그 검증기가 약하면 confident-wrong을 못 거른다. 검증기 자체의 품질·보정도 본다.

- 검증 코드가 "이 snippet이 원문에 있나"만 묻고 있으면 존재만 보는 것이다 — 그 근거가 그 문장을 뒷받침하는지는 아직 안 본 것이다.
- 답·상태·근거를 한 호출이 다 내고 코드가 그 상태를 그대로 받으면, 자기검증에 기댄 것이다. LLM이 스스로 자기 출력을 판정·교정하는 것은 외부 신호 없이 신뢰하기 어렵다.

설계 패턴: 생성 LLM과 검증을 구조로 분리한다 — 별도 스크리닝 모델, evaluator-optimizer(생성과 평가를 다른 호출로). 검증은 코드의 entailment 검사, 별도 모델, 외부 ground truth 중 하나로 LLM 바깥에서 온다.

## 측정 이음매: 실패를 보이게 만든다

- 무엇이 틀렸는지 **측정이 없으면 포인트를 못 잡는다.** 고치기 전에 실패 trace를 직접 보고 유형을 분류한다(error analysis). 데이터를 보는 마찰을 없앤다.
- 채점이 보상하는 것이 곧 모델·시스템이 통과 전략으로 배우는 것이다. "모름 인정"을 벌하고 "자신있는 찍기"를 보상하면 confident-wrong이 남는다. 검증·스코어보드가 **근거 부족한 supported(자신있는 오답)를 모르는 답과 구분**해 드러내게 한다.
- 실패 원인을 엉뚱한 컴포넌트에 귀속하지 않는다. known-good 입력을 직접 넣어 보면 생성 측 결함인지 검색 측 결함인지 갈린다.

- "근거가 틀렸다"며 검색만 계속 고치는데 그 변경이 도움이 되는지 말할 측정이 없으면, 증상을 쫓는 중이다.
- 형식·단위 테스트 통과를 제품 동작 통과로 말하지 않는다(`testing.md`). citation 일치율 같은 generic 지표 하나로 품질을 말하면, 그 지표가 못 보는 실패가 그대로 통과한다.

## 가로지르는 기준: 유창함 ≠ 정확도

- 답이 얼마나 자신있고 매끄러운지는 정답의 신호가 아니다. LLM은 정답보다 그럴듯하고 사용자 기대에 맞는 답으로 기운다(sycophancy). 사람도 확신에 찬 틀린 설명에 과의존한다.
- 그래서 코드가 신뢰할 신호를 "문장의 자신감"이 아니라 외부 근거(entailment)와 측정에 둔다.
- 위험이 큰 자료(예: 여행 예약 확인)에서는 **자신있는 오답이 모르는 답보다 더 위험하다.** supported를 늘리는 것보다 근거 부족한 supported를 줄이는 것을 우선한다.

## 근거 자료

링크는 재접근 경로다. 판단의 핵심은 위 본문에 옮겨 두었고, 아래는 그 근거의 출처다.

LLM의 성질·실패 모드:
- Language Models (Mostly) Know What They Know — Anthropic, 2022. https://arxiv.org/abs/2207.05221 — 자기평가(P(True))는 분리된 단계로는 부분적으로 작동하나 새 task에서 보정이 무너진다.
- Large Language Models Cannot Self-Correct Reasoning Yet — Huang et al., 2023. https://arxiv.org/abs/2310.01798 — 외부 피드백 없는 자기교정은 신뢰하기 어렵고 때로 역효과.
- Towards Understanding Sycophancy in Language Models — Anthropic, 2023. https://arxiv.org/abs/2310.13548 — 설득력 있는 영합적 답이 정답보다 선호되기도 한다.
- Why Language Models Hallucinate — Kalai et al., 2025. https://arxiv.org/abs/2509.04664 — 불확실성 인정을 벌하고 찍기를 보상하는 채점이 confident-wrong을 남긴다.

근거 존재 ≠ 근거가 정당화함:
- Measuring Attribution in NLG (AIS) — Rashkin et al., 2021. https://arxiv.org/abs/2112.12870 — source가 진술을 verifiable하게 뒷받침하는지를 독립 기준으로 형식화.
- Enabling LLMs to Generate Text with Citations (ALCE) — Gao et al., EMNLP 2023. https://aclanthology.org/2023.emnlp-main.398/ — citation quality를 인용이 주장을 entail하는지로 측정.
- Correctness is not Faithfulness in RAG Attributions — Wallat et al., 2024. https://arxiv.org/abs/2412.18004 — 인용의 상당수가 사후합리화이며 존재·정합만으로 불충분.
- RAGAS — Es et al., 2023. https://arxiv.org/abs/2309.15217 · faithfulness 메트릭: https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ — 답을 claim 단위로 쪼개 context가 추론으로 뒷받침하는 비율로 측정.

생성/검증 분리(이음매 패턴):
- Building Effective Agents — Anthropic, 2024. https://www.anthropic.com/research/building-effective-agents — 별도 스크리닝 모델·evaluator-optimizer, 복잡도는 결과가 개선될 때만.
- Judging LLM-as-a-Judge (MT-Bench) — Zheng et al., 2023. https://arxiv.org/abs/2306.05685 — judge의 self-enhancement bias, 높은 일치율이 높은 정확도를 함의하지 않음.
- Who Validates the Validators? — Shankar et al., UIST 2024. https://arxiv.org/abs/2404.12272 — LLM 평가기는 평가 대상의 결함을 상속한다.
- The Dual LLM pattern — Willison, 2023. https://simonwillison.net/2023/Apr/25/dual-llm-pattern/ — 한 LLM의 출력을 다른 주체가 맹신하지 말고 구조로 분리(원맥락은 prompt-injection).

eval·측정 감각:
- Your AI Product Needs Evals · A Field Guide to Rapidly Improving AI Products — Husain, 2024–2025. https://hamel.dev/blog/posts/evals/ · https://hamel.dev/blog/posts/field-guide/ — error analysis가 최고 ROI, 측정 없이 고치면 도움 여부를 말할 수 없다.
- Demystifying evals for AI agents — Anthropic, 2026. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents — 실패에서 뽑은 소수 태스크로 시작, eval이 행동 변화를 가시화.
- Task-Specific LLM Evals that Do & Don't Work — Yan, 2024. https://eugeneyan.com/writing/evals/ — source=premise, 생성물=hypothesis로 두는 NLI factual-consistency 검사.
- Common pitfalls when building gen AI — Huyen, 2025. https://huyenchip.com/2025/01/16/ai-engineering-pitfalls.html — 초기 성공이 환각 개선 난이도를 과소평가하게 한다, judge는 결정론적이지 않다.
