# Material upload 관측 record

작성일: 2026-06-10

상태: 구현된 하위 작업 spec. `POST /api/materials`의 material intake, content extraction, retrieval preparation, ready/failed 경계를 내부 observation record로 남기는 기준을 정한다.

## 왜 지금

자료함 질문 결과를 나중에 설명하려면 답변 경로만 보면 부족하다. 질문에 들어간 ready material이 어떤 업로드, parse 결과, source unit, embedding record, retrieval repository 상태에서 만들어졌는지 먼저 확인할 수 있어야 한다.

LangSmith adapter를 먼저 붙이면 외부 trace 도구가 관측 기준을 정하는 모양이 된다. 이 slice에서는 product runtime 안에서 남길 내부 record를 먼저 정하고, LangSmith는 이후 그 record를 export하는 계층으로 둔다.

## 사용자 장면

사용자가 PDF 자료를 업로드한다. API 응답은 기존처럼 `ready` 또는 `failed` material이다. 개발자는 사용자-facing 응답에 raw debug를 섞지 않고도 다음 경계를 확인할 수 있어야 한다.

- material intake가 어떤 파일명, content type, 크기로 들어왔는가.
- PDF parse가 성공했는가, 실패했다면 어떤 failure kind인가.
- parse 성공 후 질문 RAG가 읽을 source unit이 몇 개 만들어졌는가.
- embedding record가 몇 개 만들어졌고 status 분포가 어떻게 되는가.
- retrieval repository에 source unit/embedding record upsert가 실행됐는가.
- 최종 material 상태가 `ready`인지 `failed`인지.

## Goal

- `POST /api/materials` 한 요청에 대응하는 material upload observation record를 만들 수 있다.
- 이 slice는 adapter나 공통 logging helper가 아니라 product path에서 upload fact를 생성하는 leaf producer를 구현한다.
- record는 material intake, content extraction, retrieval preparation, final material status 경계를 부모 단계로 담고, leaf 단계에는 upload snapshot, PDF parse, source unit build, embedding record build, retrieval repository upsert 결과를 둔다.
- ready material 응답과 failed material 응답의 public contract는 바꾸지 않는다.
- observation record는 원본 PDF, 추출 전문, embedding vector, provider raw response를 저장하지 않는다.
- 관측 record 생성 실패나 비활성화가 material upload 결과를 바꾸지 않는다.

## Rules

- observation은 product path를 관찰하는 side effect다. material status를 결정하는 주체가 되면 안 된다.
- record shape의 소유자는 adapter가 아니라 `/api/materials` upload event다.
- successful upload record는 `materialId`, final status, page count, source unit count, embedding status counts, repository upsert summary를 남길 수 있다.
- failed upload record는 final status와 failure kind를 남기되, 내부 exception stack이나 원본 파일 내용을 저장하지 않는다.
- PDF가 아닌 파일, parse 실패, 너무 큰 파일은 서로 다른 failure kind로 구분할 수 있어야 한다.
- SourceUnit text와 embedding vector는 기본 record에 넣지 않는다. 필요하면 id/count/status summary만 남긴다.
- retrieval repository upsert가 실패하면 ready material로 publish하지 않는 기존 동작을 유지하고, record에는 repository boundary 실패를 요약한다.

## Non-goals

- LangSmith trace export는 이 문서의 범위가 아니다.
- `/api/questions` 관측 record나 answer snapshot은 만들지 않는다.
- provider/model/retrieval config snapshot 전체를 확정하지 않는다.
- observation record 저장소의 장기 보관, 검색 UI는 정하지 않는다.
- material API 응답에 debug field를 추가하지 않는다.

## 현재 코드에서 볼 곳

- `apps/server/api/routes/materials.py`: upload request, file size 제한, PDF 여부 확인, `parse_pdf`, `store.add_ready`, `store.add_failed`를 연결한다.
- `apps/server/materials/store.py`: ready material 생성, source unit build, embedding record build, retrieval repository upsert, failed material 생성을 담당한다.
- `apps/server/materials/pdf.py`: PDF parse 성공/실패 경계다.
- `apps/server/retrieval/chunking.py`: parsed text를 source unit으로 나눈다.
- `apps/server/retrieval/embeddings.py`: source unit별 embedding record를 만든다.
- `apps/server/retrieval/repository.py`: source unit과 embedding record를 material 단위로 저장한다.
- `apps/server/materials/observation.py`: material upload observation record, step model, sink protocol, 테스트용 in-memory sink를 정의한다.
- `apps/server/tests/test_materials_api.py`: ready/failed upload와 source unit/embedding record 동작을 확인한다.

## 구현면 펼치기

| 구현 요소 | 필요한 이유 | 현재 코드/문서 | 처음 닫을 기준 |
| --- | --- | --- | --- |
| Material upload observation model | 한 업로드 요청의 관측 결과를 안정된 형태로 남겨야 한다 | `materials/observation.py`에 parent/leaf step record가 있다 | material intake, extraction, retrieval preparation, finalization 아래에 upload summary, phase outcomes, counts, final status, failure kind를 담는 내부 record가 있다 |
| Observation sink | record 생성과 저장 방식을 product logic에서 분리해야 한다 | 테스트용 in-memory sink가 있고, export 비활성화는 no-op exporter가 담당한다 | export가 비활성화돼도 product 응답이 바뀌지 않는다 |
| Route boundary capture | file name, content type, size, upload 수용 실패는 route에서만 알 수 있다 | `routes/materials.py`가 upload facts와 upload/pdf_parse 실패를 기록한다 | too large, unsupported type, parse attempt 전후 상태를 record에 반영한다 |
| Store boundary capture | source unit, embedding record, retrieval upsert 결과는 store에서 만들어진다 | `materials/store.py`가 source unit, embedding, repository upsert 결과를 기록한다 | source unit count, embedding status counts, repository upsert outcome을 record에 반영한다 |
| Failure summary | 실패를 나중에 비교하려면 failure kind가 필요하다 | 내부 record가 public error string과 별도로 failure kind를 가진다 | unsupported file, parse failed, size limit, repository upsert failed를 구분한다 |
| Tests | record가 product response를 오염시키지 않아야 한다 | `test_materials_api.py`가 response contract와 internal record를 함께 확인한다 | ready/failed 응답은 유지되고 internal record만 추가로 확인한다 |

## 이번 AC

1. 정상 PDF 업로드는 기존 `ready` material 응답을 유지하면서 upload snapshot, parse success, source unit count, embedding status counts, repository upsert summary, final status `ready`를 담은 internal observation record를 만든다.
2. PDF가 아닌 파일과 parse 실패는 기존 `failed` material 응답을 유지하면서 failure kind와 final status `failed`를 담은 internal observation record를 만든다.
3. 너무 큰 파일과 retrieval repository upsert 실패는 기존 public 동작을 바꾸지 않고, 관측 가능한 실패 boundary를 record에 요약한다.
4. observation record에는 원본 PDF, 추출 전문, embedding vector, provider raw response, stack trace가 들어가지 않는다.
5. observation sink가 비활성화되어도 `POST /api/materials`의 product 응답 계약은 동일하다.

## 구현 결과

2026-06-11 현재 이 slice는 `apps/server/materials/observation.py`와 `/api/materials` route/store 연결로 구현됐다.

내부 record는 한 요청을 parent/leaf step으로 남긴다. 부모 단계는 제품 파이프라인을 읽기 위한 묶음이고, leaf 단계가 실제 code boundary에서 생긴 fact를 가진다.

```text
material_upload
  material_intake
    upload_snapshot
  content_extraction
    pdf_parse
  retrieval_preparation
    source_unit_build
    embedding_record_build
    retrieval_repository_upsert
  finalization
    material_status
```

각 step은 `not_started`, `succeeded`, `failed` 중 하나의 status를 가진다. 부모 step의 status와 failure kind는 자식 leaf에서 파생한다. step별 facts는 allowlist로 제한한다.

| Step | 남기는 facts | 실패 예 |
| --- | --- | --- |
| `upload_snapshot` | `file_name`, `content_type`, `size_bytes`, `size_limit_bytes` | `unsupported_file`, `size_limit_exceeded` |
| `pdf_parse` | `page_count` | `parse_failed` |
| `source_unit_build` | `count` | `source_unit_build_failed` |
| `embedding_record_build` | `count`, `status_counts` | `embedding_record_build_failed` |
| `retrieval_repository_upsert` | `executed`, `source_unit_count`, `embedding_record_count` | `repository_upsert_failed` |
| `material_status` | `status` | 없음 |

`source_unit_build`는 현재 구현에서 chunking 경계다. PDF parse 결과의 text를 `SourceUnit`으로 나누는 단계이며, SourceUnit text 자체는 observation record에 넣지 않는다.

기본 sink는 export sink(미설정 시 no-op exporter)이고, 테스트에서는 in-memory sink로 record를 확인한다. sink가 실패해도 product 응답과 저장 흐름을 바꾸지 않는다.

## 구현 중 결정

- 내부 record를 LangSmith보다 먼저 둔다. LangSmith는 product 관측 기준을 정하는 주체가 아니라, 내부 record를 외부 trace로 내보내는 선택적 sink/exporter다.
- record는 flat field 묶음보다 parent/leaf step 구조로 둔다. 이후 LangSmith/OpenTelemetry 계층으로 보낼 때 부모 단계는 trace/run 묶음으로, leaf 단계는 event나 span detail로 매핑하기 쉽고, `POST /api/materials` 흐름도 질문 RAG의 upstream 준비 과정처럼 읽힌다.
- `validation`은 별도 step으로 두지 않는다. PDF 여부와 size limit은 독립 처리 단계가 아니라 material intake 수용 실패에 가까우므로 `upload_snapshot` leaf의 failure kind로 남긴다.
- recorder는 단계별 전용 메서드를 계속 늘리지 않고 `succeed(step, facts)`, `fail(step, failure_kind)`, `finalize(...)` 중심으로 둔다. 목적은 product orchestration을 recorder가 다시 소유하지 않게 하는 것이다.
- step facts는 allowlist 방식으로 제한한다. 원본 PDF, 추출 전문, SourceUnit text, embedding vector, provider raw response, stack trace가 들어갈 경로를 만들지 않는다.
- retrieval repository upsert 실패는 기존처럼 ready material로 publish하지 않는다. observation은 이 실패를 `repository_upsert_failed`로 기록하되, product 상태 결정의 주체가 되지 않는다.

## 확인 방법

1. `uv run pytest apps/server/tests/test_materials_api.py`
2. 정상 PDF 업로드 테스트에서 ready response와 internal observation record의 count/status summary를 함께 확인한다.
3. blank PDF나 PDF가 아닌 파일 테스트에서 failed response와 failure kind record를 확인한다.
4. retrieval repository upsert 실패 테스트에서 ready material로 publish되지 않는 기존 동작과 failure boundary record를 확인한다.
5. API 응답 payload에 observation/debug field가 추가되지 않았는지 확인한다.

현재 확인된 테스트:

- `uv run pytest apps/server/tests/test_materials_api.py`
- `uv run pytest apps/server/tests`
- `git diff --check`

## 남은 판단

- observation record를 요청 중 sink에만 둘지, local run artifact로도 남길지.
- record id를 request id, material id, 또는 별도 observation id 중 무엇으로 삼을지.
- file name과 content type을 내부 record에는 그대로 두되, 외부 exporter에서는 summary나 hash로 줄일지.
- repository upsert 실패처럼 public response가 material이 아닌 예외인 경우 record 조회 경로를 어떻게 둘지.
