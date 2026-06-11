# Eval Run 기록

실제 product flow가 생긴 뒤에만 run artifact를 여기에 둔다.

placeholder score를 만들지 않는다. run 기록은 관찰한 failure, 관련 product change, 다음 verification point를 연결한다.

`question-runtime-recording/` 아래 run은 `eval/question_runtime_recording_smoke.py`가 만든 local smoke artifact다. 이 artifact는 점수나 완료 proof가 아니라, product request header와 observation export JSONL이 같은 `correlation_id`로 연결되는지 확인하기 위한 기록이다.

`question-runtime-recording/` 경로는 `.gitignore`에 포함되어 있다. 공유할 필요가 있는 run은 raw source text, raw question, raw LLM payload, secret이 없는지 먼저 확인한 뒤 별도 판단으로 다룬다.

수동/개인 자료 run은 raw source text, raw question, raw LLM payload, secret을 저장하지 않는다.
