# Eval run correlation artifact

작성일: 2026-06-11

상태: 구현된 하위 작업 spec. question runtime recording을 수동/반복 확인할 때 eval run artifact와 observation export를 같은 `correlation_id`로 연결하는 기준을 정한다.

## 왜 지금

01-07에서 product 경로의 prompt, material/question observation, runtime config snapshot, local/LangSmith export, request/correlation id가 닫혔다. 이제 남은 문제는 한 번의 product smoke run을 나중에 다시 볼 때 eval run 기록과 local observation JSONL을 어떤 id로 함께 찾을지다.

이 slice는 metric threshold나 점수 체계를 만드는 일이 아니다. product entry point를 호출한 관찰 run이 어느 request와 observation export에 해당하는지 얇게 남긴다.

## 사용자 장면

개발자가 같은 체크인 자료 장면을 한 번 실행한다.

```text
eval runner
  -> POST /api/materials
  -> POST /api/questions with X-TripProof-Correlation-Id
  -> eval run artifact
  -> local observation JSONL
```

나중에 개발자는 eval run artifact의 `correlation_id`로 local observation JSONL record를 찾고, public response body가 debug id를 노출하지 않았는지 함께 확인할 수 있어야 한다.

## Goal

- eval run artifact는 `correlation_id`를 top-level로 소유한다.
- material upload request와 question request의 response header `request_id`/`correlation_id`를 기록한다.
- local observation JSONL 경로와 record 요약을 artifact에서 찾을 수 있게 한다.
- `correlation_id`로 local observation JSONL record를 다시 찾는 helper를 둔다.
- artifact는 raw source text, raw question, raw LLM payload, secret을 저장하지 않는다.
- product code는 eval runner나 eval artifact를 import하지 않는다.

## Rules

- eval은 product code를 호출하는 관찰자다. product route, observation exporter, request/correlation middleware는 실제로 지나가야 한다.
- 첫 구현은 외부 server process나 LangSmith API key 없이 재현 가능한 `FastAPI TestClient` smoke run으로 둔다.
- static composer를 쓰는 경우 artifact에 `answer_composer=eval_static_evidence`로 명시한다. 이 run은 모델 품질 평가가 아니라 correlation/export 연결 smoke다.
- product response JSON에는 `requestId`, `correlationId`를 추가하지 않는다.
- eval artifact는 public response의 요약, 상태, item count, evidence state count처럼 안전한 관찰 요약만 남긴다.
- observation export JSONL은 기존 `observation_export.v1` envelope를 그대로 쓴다. eval artifact는 그 파일을 소유하지 않고 경로와 record 요약만 참조한다.

## Artifact shape

첫 schema version:

```text
tripproof.eval_run.question_runtime_recording.v1
```

필수 top-level:

- `run_id`
- `created_at`
- `kind`
- `correlation_id`
- `product_entry_point`
- `runtime`
- `requests`
- `observed_answer`
- `observation_export`
- `checks`
- `next_verification_point`

`requests.material_upload`는 header가 없던 upload 요청이 `correlation_id=request_id` fallback으로 남았는지 기록한다.

`requests.question_answer`는 eval runner가 보낸 `X-TripProof-Correlation-Id`가 response header와 observation export에 유지됐는지 기록한다.

## 구현 결과

- `eval/question_runtime_recording_smoke.py`를 추가했다.
- runner는 `TestClient(create_app(...))`로 `POST /api/materials`, `POST /api/questions` product entry point를 호출한다.
- runner는 `LocalArtifactObservationExporter`를 임시 run directory에 붙여 `observations/observation-export.jsonl`을 만든다.
- question request에는 `X-TripProof-Correlation-Id`를 보낸다.
- `run.json`에는 `correlation_id`, request/response header id, observation export path, operation별 export 요약, public answer summary/count/check 결과를 남긴다.
- 기본 output directory인 `eval/runs/question-runtime-recording/`은 local run artifact 경로라 `.gitignore`에 포함했다.
- `eval/README.md`와 `eval/runs/README.md`는 기본 runner 산출물이 로컬 전용이고, 공유/commit은 별도 판단으로 다룬다는 점을 명시한다.
- `apps/server/tests/test_eval_question_runtime_recording_smoke.py`는 runner가 artifact와 observation JSONL을 만들고, question observation export가 같은 correlation id를 갖는지 확인한다.
- `eval/find_observation_by_correlation.py`는 `.tripproof-observations/`와 `eval/runs/question-runtime-recording/` 아래 JSONL export를 검색해 correlation id가 같은 record를 찾는다.
- lookup helper 출력은 operation, request id, final status, failure kind, material id, source path/line 같은 안전한 요약만 포함한다.

## Non-goals

- metric score, pass/fail threshold, benchmark dataset을 만들지 않는다.
- real LangSmith API 호출을 필수로 만들지 않는다.
- raw source text, raw question, answer body, evidence snippet을 eval artifact에 저장하지 않는다.
- product code가 eval runner나 run artifact를 읽게 만들지 않는다.

## 이번 AC

1. eval smoke runner는 product material/question entry point를 호출하고 run artifact를 만든다.
2. run artifact top-level `correlation_id`는 question response header와 question observation export의 `correlation_id`와 같아야 한다.
3. local observation JSONL은 `material_upload`, `question_answer` 두 record를 남겨야 한다.
4. product JSON body에는 request/correlation id가 없어야 한다.
5. runner와 artifact는 eval 영역에만 있고 product code는 eval을 import하지 않는다.
6. 기본 output directory에 생기는 local run artifact는 git status를 더럽히지 않아야 한다.
7. lookup helper는 `correlation_id`로 local observation export record를 찾되 raw step facts나 source/question/LLM payload를 출력하지 않아야 한다.

## 확인 방법

```bash
uv run python eval/question_runtime_recording_smoke.py \
  --correlation-id flow_eval_test \
  --json
```

생성된 `run.json`에서 다음을 확인한다.

- `correlation_id == "flow_eval_test"`
- `requests.question_answer.correlation_id == "flow_eval_test"`
- `observation_export.records`의 `question_answer.correlation_id == "flow_eval_test"`
- `checks`의 모든 값이 `true`

테스트:

```bash
uv run pytest apps/server/tests -q
```

기본 산출물 경로가 ignore되는지 확인:

```bash
git check-ignore eval/runs/question-runtime-recording/example/run.json
```

local observation export lookup:

```bash
uv run python eval/find_observation_by_correlation.py flow_eval_test
```

## 남은 판단

- 실제 수동 자료 run artifact를 commit할지, 로컬 산출물로만 둘지.
- LangSmith trace URL/id를 artifact나 lookup 결과에 나중에 붙일지.
- eval artifact retention/cleanup을 local observation artifact rotation과 같이 다룰지.
