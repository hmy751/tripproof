# Raw Notes - Observation Record와 Trace Provider 경계

이 파일은 `index.md` 관찰의 배경 재료다. 현재 실행 기준이나 작업 대기열이 아니다.

## 왜 raw가 필요한가

`POST /api/materials` observation record 구현 중 record shape와 sink 역할을 설명하는 과정에서, 내부 record가 LangSmith trace와 같은 것인지에 대한 질문이 생겼다. 그 질문은 단순 용어 혼동이 아니라 이후 `/api/questions` observation, config snapshot, LangSmith adapter 작업에서도 반복될 수 있는 설계 경계였다.

## 대화·검토에서 드러난 문제 감각

- `MaterialUploadObservationRecorder`에 단계별 전용 메서드가 늘어나면 recorder가 product orchestration을 다시 소유하는 것처럼 보일 수 있다.
- observation record를 flat summary로만 두면 실제 실행 흐름을 보기 어렵고, LangSmith/OpenTelemetry 같은 trace tree로 export하기도 어색하다.
- 반대로 계층적으로 수집한다는 이유로 raw PDF, 추출 전문, source unit text, embedding vector, provider raw response까지 넣으면 product 관측 계약이 debug dump로 변한다.
- `validation`은 upload 이후 별도 처리 단계처럼 보였지만, 실제로는 size/content-type 수용 여부 확인이라 `upload` step의 failure kind로 두는 편이 자연스럽다.

## 확인된 사실과 해석

- `apps/server/materials/observation.py`는 `MaterialUploadObservationRecord`를 `operation`, ordered `steps`, `final_material_status`, `failure_kind`로 정의한다.
- 현재 step order는 `upload`, `pdf_parse`, `source_unit_build`, `embedding_record_build`, `retrieval_repository_upsert`다.
- step facts는 allowlist로 제한된다.
  - `upload`: `file_name`, `content_type`, `size_bytes`, `size_limit_bytes`
  - `pdf_parse`: `page_count`
  - `source_unit_build`: `count`
  - `embedding_record_build`: `count`, `status_counts`
  - `retrieval_repository_upsert`: 없음
- `unsupported_file`, `size_limit_exceeded`는 `upload` step failure로 기록한다.
- `parse_failed`는 `pdf_parse` failure로 기록한다.
- `repository_upsert_failed`는 `retrieval_repository_upsert` failure로 기록하고, 기존처럼 ready material로 publish하지 않는다.
- 기본 sink는 no-op이고 테스트는 in-memory sink를 사용한다.
- API 응답 contract에는 observation/debug/raw field를 추가하지 않는다.

## 기각·보류된 후보

- LangSmith를 바로 관측 기준으로 삼는 방향은 보류했다. LangSmith는 내부 record를 소비하는 optional sink/exporter로 두는 편이 product contract와 provider 경계를 분리한다.
- `validation` step은 제거했다. 처리 단계라기보다 upload 수용 실패이므로 `upload` failure kind로 접었다.
- step마다 전용 메서드를 두는 방식은 축소했다. `succeed(step, facts)`, `fail(step, failure_kind)`, `finalize(...)` 중심이 이후 step 추가에 덜 취약하다.
- local run artifact 저장은 이번 slice에서 정하지 않았다.
- 외부 exporter에서 file name/content type을 그대로 보낼지 hash/redact할지는 남은 판단이다.

## 재진입 메모

다음 observation 작업에서 먼저 볼 질문:

- 새 step이 실제 product processing stage인가, 아니면 작은 check인가?
- step facts가 원인 분석에 필요한 safe summary인가, raw/debug payload인가?
- LangSmith가 꺼져도 product response와 내부 record 생성이 동일하게 유지되는가?
- exporter가 record shape의 소유자가 되고 있지 않은가?
