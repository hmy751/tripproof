# 2026-06-11 - Observation Record와 Trace Provider 경계

## 폴더 구성

- `index.md`: 다음 구현에서 먼저 볼 관찰과 경계.
- `raw.md`: 이 관찰의 배경 재료.

`raw.md`는 현재 실행 기준이나 작업 대기열이 아니다. 현재 작업에 적용할 때는 이 `index.md`와 현재 코드 상태를 먼저 본다.

## 왜 남기나

`POST /api/materials` observation record를 구현하면서 내부 record와 LangSmith trace의 역할이 쉽게 겹쳐 보였다. 둘 다 실행 단계, 상태, metadata를 담을 수 있기 때문이다.

이 노트는 외부 trace provider를 구현 기준으로 삼는 drift를 막고, product runtime 안에서 먼저 정해야 할 관측 계약이 무엇인지 보정하기 위해 남긴다.

## 관찰

내부 observation record는 LangSmith를 대체하는 작은 trace system이 아니다. TripProof product path가 어떤 domain fact를 만들었는지, 어떤 failure kind로 멈췄는지, 어떤 safe facts만 남길지 정하는 계약이다.

LangSmith나 OpenTelemetry는 이 record를 보기 좋은 trace/run/event로 내보내는 export 계층이다. 이 순서가 뒤집히면 provider가 제공하는 trace 모양이 product 관측 기준을 정하게 되고, `unsupported_file`, `parse_failed`, `repository_upsert_failed` 같은 도메인 실패 구분이 흐려질 수 있다.

단계 구조도 같은 이유로 처리 흐름 중심이어야 한다. `validation`처럼 독립 산출물을 만들지 않는 generic checkpoint를 step으로 승격하면 record tree가 실제 material processing flow보다 관측 구현의 편의에 맞춰진다. 파일 크기 초과나 PDF 아님은 별도 processing stage가 아니라 `upload` step의 수용 실패로 두는 편이 읽기 쉽다.

## 다시 볼 경계

Internal record first, exporter last.

내부 record는 product가 보장하는 관측 계약이고, external trace provider는 그 계약을 소비하는 sink/exporter다. LangSmith가 꺼져도 product response와 내부 record 생성 경계는 동일해야 한다.

Ordered steps are processing stages, not every check.

`material_upload`의 현재 단계는 `upload -> pdf_parse -> source_unit_build -> embedding_record_build -> retrieval_repository_upsert`다. upload 단계 안의 size/content-type 거절은 `upload failed`로 남긴다. `source_unit_build`는 chunking 경계이며, source unit text 자체를 저장하지 않는다.

Safe facts by allowlist.

계층적으로 잘 수집한다는 것은 raw payload를 깊게 저장한다는 뜻이 아니다. 각 step에는 allowlist된 작은 facts만 남긴다. 원본 PDF, 추출 전문, source unit text, embedding vector, provider raw response, stack trace가 들어갈 경로를 만들지 않는다.

## Calibration sample

피할 형태:

- LangSmith trace shape를 먼저 정하고 product record를 거기에 맞춘다.
- `validation`, `precheck`, `guard`처럼 일반 checkpoint를 처리 단계와 같은 높이로 계속 추가한다.
- 디버깅 편의를 이유로 full text, vector, raw provider response를 step facts에 넣는다.
- recorder가 product orchestration을 다시 소유할 만큼 단계별 전용 메서드를 계속 늘린다.

기준 형태:

- `/api/materials`가 upload facts와 upload failure kind를 만든다.
- store boundary가 source unit count, embedding status counts, repository upsert outcome을 만든다.
- record는 ordered steps와 final material status를 가진다.
- sink는 no-op, in-memory, file, LangSmith 같은 출력 계층으로 교체 가능하다.

Check:

- 이 step은 실제 product processing stage인가, 아니면 작은 check인가?
- 이 fact는 나중에 원인 분석에 필요한 safe summary인가, raw payload인가?
- LangSmith 없이도 이 record의 의미를 이해할 수 있는가?
- exporter가 실패해도 product response contract가 유지되는가?

## 어디에는 남기지 않았나

`docs/decisions/`에는 남기지 않았다. 특정 provider나 저장소를 채택/기각한 결정이 아니라, 관측 구현 중 반복될 수 있는 역할 경계 관찰이다.

`docs/work-log.md`에는 남기지 않았다. 다음 작업 재진입 상태나 TODO가 아니라, 이후 material/question observation 구현에서 다시 볼 calibration sample이다.

`docs/specs/`에는 구현 결과와 이번 slice의 record shape만 남겼다. LangSmith와 내부 record의 역할 혼동, 단계 승격 기준, raw payload 금지 감각은 spec AC보다 implementation note가 더 적절하다.
