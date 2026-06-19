# Eval Run 기록

실제 product flow가 생긴 뒤에만 run artifact를 여기에 둔다.

가짜 score를 만들지 않는다. run 기록은 관찰한 failure, 관련 product change, 다음 verification point를 연결한다.

`question-runtime-recording/` 아래 run은 `eval/question_runtime_recording_smoke.py`가 만든 local smoke artifact다. 이 artifact는 점수나 완료 proof가 아니라, product request header와 observation export JSONL이 같은 `correlation_id`로 연결되는지 확인하기 위한 기록이다.

`eval/runs/` 아래 파일은 eval을 돌릴 때 생기는 실행 결과다. runner에 따라 디버그 편의를 위해 제품 응답을 넓게 남길 수도 있고, 비교에 필요한 요약만 남길 수도 있다. 역할은 제품 behavior 관찰용 local artifact이며, 공유 문서는 파일 복사가 아니라 failure, 관련 product change, 다음 verification point를 별도로 요약해 작성한다.

local observation export를 다시 찾을 때는 `eval/find_observation_by_correlation.py`에 `correlation_id`를 넘긴다.

공유가 필요하면 결과 파일을 복사하지 않고, 관찰한 failure, 관련 product change, 다음 verification point만 별도 요약으로 작성한다.
