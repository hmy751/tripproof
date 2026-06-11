# Eval 영역

product entry point가 생긴 뒤 eval code를 여기에 둔다.

eval은 product code를 호출하고 결과를 기록하면서 product behavior를 관찰한다. product logic은 product 쪽에 둔다.

## 현재 runner

```bash
uv run python eval/question_runtime_recording_smoke.py \
  --correlation-id flow_eval_test \
  --json
```

이 runner는 metric score가 아니라 question runtime recording smoke다. `POST /api/materials`와 `POST /api/questions` product entry point를 호출하고, 생성된 run artifact와 local observation JSONL이 같은 `correlation_id`로 연결되는지 확인한다.

기본 산출물은 `eval/runs/question-runtime-recording/<run-id>/` 아래에 생긴다. 이 경로는 local run artifact라 `.gitignore`에 포함되어 있고, 실제 수동 run artifact를 commit할지는 별도 판단으로 둔다.

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
