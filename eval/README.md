# Eval 영역

product entry point가 생긴 뒤 eval code를 여기에 둔다.

eval은 product code를 호출하고 결과를 기록하면서 product behavior를 관찰한다. product logic은 product 쪽에 둔다.

## 현재 runner

질문셋을 product API로 실행하고 HTML report까지 만들 때는 다음 runner를 쓴다.

```bash
uv run python eval/run_question_dataset.py \
  --question-limit 3 \
  --json
```

기본 실행은 앱의 production config에 가까운 runtime을 사용한다. runner가 fake embedding이나 `missing` answer composer를 기본으로 주입하지 않고, `create_app()`이 읽는 설정에 따라 실제 answer composer, embedding provider/generation, retrieval backend를 탄다. 각 질문은 별도 `correlation_id`를 갖고, `run.json`의 `question_results`와 observation JSONL의 `question_answer` record는 그 값으로 연결된다.

원문 Agoda PDF baseline을 만들 때는 실제 PDF를 그대로 넘긴다.

```bash
uv run python eval/run_question_dataset.py \
  --material-pdf-file fixtures/private/accommodation-checkin/agoda-fukuoka-booking-confirmation-private.pdf \
  --json
```

`--material-pdf-file`을 쓰면 `run.json`의 `run_purpose.id`가 `original_pdf_baseline`으로 남는다. 기본 text fixture 실행은 `sample_fixture_smoke`로 남으며, product API와 report join 확인용이지 원문 PDF 개선 근거로 해석하지 않는다.

빠른 smoke나 renderer 테스트처럼 외부 provider 품질을 보지 않을 때만 deterministic mode를 명시한다.

```bash
uv run python eval/run_question_dataset.py \
  --runtime-mode deterministic \
  --question-limit 3 \
  --json
```

`--runtime-mode deterministic`은 fake embedding, memory retrieval, 기본 `missing` answer composer를 쓰는 test-double 실행이다. 이 run은 product API와 report join 확인용이며 원문 PDF QA 품질 baseline으로 해석하지 않는다.

가장 얇은 correlation smoke만 확인하려면 다음 runner를 쓴다.

```bash
uv run python eval/question_runtime_recording_smoke.py \
  --correlation-id flow_eval_test \
  --json
```

이 smoke runner는 metric score가 아니라 question runtime recording smoke다. `POST /api/materials`와 `POST /api/questions` product entry point를 호출하고, 생성된 run artifact와 local observation JSONL이 같은 `correlation_id`로 연결되는지 확인한다.

기본 산출물은 runner에 따라 `eval/runs/question-dataset/<run-id>/` 또는 `eval/runs/question-runtime-recording/<run-id>/` 아래에 생긴다. 이 경로는 local run artifact라 `.gitignore`에 포함되어 있고, 실제 수동 run artifact를 commit할지는 별도 판단으로 둔다.

한 run directory에서 먼저 볼 파일은 다음 순서다.

1. `report.html`: 사람이 보는 joined view다. 실패 질문을 고르고 product answer, retrieval candidate text, composer context, answer evidence, observation file 위치를 한 화면에서 본다.
2. `run.json`: eval 실행 결과와 rule check의 machine-readable index다. 실행 조건, request id, `correlation_id`, observed answer summary, observation path를 확인한다.
3. `observations/observation-export.jsonl`: product runtime observation trace다. report의 observation 위치를 따라가면 같은 `correlation_id`의 raw step payload를 볼 수 있다.
4. LangSmith: 설정된 경우 같은 `correlation_id`로 외부 trace UI에서 operation/step tree summary를 찾는다. 기본 LangSmith payload는 전문 text를 보내지 않고, 전문 확인은 local observation/report가 맡는다.

`report.html`은 source of truth가 아니다. `run.json`과 observation JSONL을 읽어 붙인 view이며, product API response body나 product code가 report에 의존하지 않는다.

이미 만들어진 run에서 report만 다시 렌더링하려면 다음 명령을 쓴다.

```bash
uv run python eval/html_report.py eval/runs/question-runtime-recording/<run-id>/run.json
```

local observation export를 correlation id로 다시 찾을 때는 lookup helper를 쓴다.

```bash
uv run python eval/find_observation_by_correlation.py flow_eval_test
```

기본 검색 위치는 `.tripproof-observations/`와 `eval/runs/question-runtime-recording/`이다. 출력은 operation, request id, final status, failure kind, 파일 위치 같은 안전한 요약만 포함한다.

product flow가 생긴 뒤 고려할 수 있는 evaluation axis:

- Faithfulness/Groundedness
- Citation Precision
- Abstention F1
- Conflict Recall

이 이름들은 아직 run result, threshold, 완료된 proof가 아니다.
