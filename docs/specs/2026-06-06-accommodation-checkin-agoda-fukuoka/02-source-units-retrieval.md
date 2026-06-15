# 숙소 체크인 02 - SourceUnit과 RAG search boundary

상태: `SourceUnit` boundary와 Supabase vector retrieval backend 연결 구현.

부모: [숙소 체크인 확인 - Agoda 후쿠오카 예약 PDF](index.md)

## 왜 지금

PDF 본문을 긴 문자열 하나로 AI나 extractor에 넘기면, 나중에 답변과 fact가 실제 원문 어디에서 왔는지 추적하기 어렵다. 이번 단계는 01에서 파싱한 PDF 본문을 locator가 있는 `SourceUnit`으로 나누고, RAG 검색이 `SourceUnit` 원문으로 되돌아갈 수 있는 boundary를 잡는 데까지 닫는다.

이 단계는 답을 찾거나 근거를 확정하는 단계가 아니다. `SourceUnit`은 원문이고, `search_text`와 embedding/vector는 그 원문을 다시 찾기 위한 파생물이다. `RetrievedSource` 후보, 검증된 `EvidenceRef`, `FactCandidate`, `EvidenceState` 판단은 03 이후에서 다룬다.

## 사용자 장면

사용자는 Agoda 예약 확정 PDF를 넣고 전체 자료함에 묻는다.

```text
체크인 때 뭘 보여줘야 해? 체크인 시간은 몇 시야?
```

제품은 답을 만들기 전에 PDF 원문을 잃지 않는 단위로 보존하고, 나중에 질문이나 extraction target으로 관련 `SourceUnit`을 찾을 수 있는 search boundary를 준비해야 한다.

## RAG 기본 흐름

```text
StoredMaterial(text, fileName, pageCount)
-> SourceUnit[]
-> SourceUnit.search_text + EmbeddingRecord[]
-> lexical search / vector search
-> RetrievedSource[] / AnswerContext
-> 03 grounding + ChatAnswer/EvidenceRef boundary
```

TripProof에서 이 흐름의 소유권은 아래처럼 나눈다.

- 02는 `SourceUnit`과 `EmbeddingRecord`를 만든다.
- `SourceUnit.search_text`와 embedding/vector는 `SourceUnit`을 찾기 위한 파생물이다.
- `RetrievedSource` 후보와 `AnswerContext`는 아직 사용자-facing evidence가 아니다.
- 검증된 `EvidenceRef`와 `supported` / `missing` 판단은 03 이후 `SourceUnit` 원문을 다시 확인한 뒤 만든다.

## Goal

- `SourceUnit` 생성 입력은 01에서 파싱된 PDF 본문을 받는다.
- 파싱 본문은 Python 구현 기준 `material_id`, `file_name`, `page`, `unit_index`, `locator`, `text`, `search_text`를 가진 `SourceUnit`으로 나뉜다.
- 각 `SourceUnit`은 나중에 원문 일부를 그대로 snippet으로 회수할 수 있어야 한다.
- `search_text`는 `SourceUnit`에서 파생된 검색용 text이며, 원문 truth는 `SourceUnit.text`다.
- embedding vector를 만들더라도 vector는 `SourceUnit`을 찾기 위한 색인이고, 근거 자체가 아니다.
- 등록되지 않은 companion source의 값은 현재 PDF `SourceUnit`이나 embedding record로 섞지 않는다.

## Rules

- `SourceUnit`은 답변, fact, 검증된 `EvidenceRef`가 아니다. 원문을 다시 찾기 위한 최소 근거 단위다.
- `search_text`는 `SourceUnit`에서 파생된다. 원문 truth의 주인은 항상 `SourceUnit.text`와 locator다.
- embedding/vector DB를 붙여도 `vector -> source_unit_id -> SourceUnit.text`로 되돌아올 수 있어야 한다.
- lexical search, embedding search, rerank는 모두 retrieval 후보를 만들기 위한 방법일 뿐, `supported`를 결정하지 않는다.
- `SourceUnit`은 최소한 `material_id`, `file_name`, `page`, `unit_index`, `locator`, `text`, `search_text`를 가진다.
- `EmbeddingRecord`는 최소한 `source_unit_id`, `provider`, `model`, `dimensions`, `status`, `vector`를 가진다.
- 체크인 제시물, 체크인 시작 시각, 날짜 같은 도메인 target 판정은 02에 넣지 않는다.
- 질문 히스토리나 일반 호텔 지식으로 현재 등록된 source boundary를 넓히지 않는다.

## Non-goals

- 체크인 제시물, 체크인 날짜, 체크인 시작 시각 판정.
- `EvidenceRef` source 선택이나 rejected candidate 판정.
- `FactCandidate`, `EvidenceRef`, `EvidenceState` 생성.
- 답변 문장 생성, 카드 초안, 대시보드, 현장 카드.
- vector DB 운영 튜닝, background embedding job, 장기 보관 정책 확정.
- 모든 PDF 형식에 맞는 semantic chunking.
- OCR, bbox, visual region locator.
- eval metric dashboard.

## 현재 코드에서 볼 곳

- `apps/server/app.py`: `MaterialStore`가 앱 상태에 연결된다.
- `apps/server/core/config.py`: embedding provider/model/dimensions와 auto-generate flag의 env 기본값을 둔다.
- `apps/server/materials/pdf.py`: PDF text가 `[page N]` 마커와 함께 만들어진다.
- `apps/server/materials/store.py`: ready material을 저장할 때 `SourceUnit`과 `EmbeddingRecord`를 함께 만든다.
- `apps/server/retrieval/models.py`: `SourceUnit`과 `EmbeddingRecord` 경계.
- `apps/server/retrieval/chunking.py`: `[page N]` 마커를 page locator가 있는 `SourceUnit`으로 나눈다.
- `apps/server/retrieval/embeddings.py`: Ollama embedding provider와 pending/ready/failed `EmbeddingRecord` 생성.
- `apps/server/retrieval/repository.py`: in-memory repository와 vector match 계약을 둔다.
- `apps/server/retrieval/supabase.py`: Supabase REST 기반 `source_units` / `source_embeddings` 저장소와 vector match adapter를 둔다.
- `apps/server/retrieval/search.py`: Supabase vector match를 우선 사용하고, ready vector나 vector match 결과가 없으면 lexical fallback으로 `RetrievedSource` 후보를 고른다. 체크인 도메인 target 규칙은 넣지 않는다.
- `apps/server/use_cases/questions.py`: `/api/questions`가 현재 public response에 싣는 `QuestionResponse.answer` 경로에서 retrieval records, `AnswerContext`, answer composer를 연결한다.
- `supabase/migrations/20260609_tripproof_retrieval.sql`: pgvector extension, `source_units` / `source_embeddings` table, HNSW index, match RPC를 정의한다.

## 기본 흐름

```text
StoredMaterial(text, fileName, pageCount)
-> SourceUnit(material_id, file_name, page, unit_index, locator, text, search_text)
-> EmbeddingRecord(source_unit_id, provider, model, dimensions, vector, status)
-> RetrievalRepository(source_units, embedding_records)
```

02의 관찰 대상은 `SourceUnit`과 `EmbeddingRecord`가 원문 위치로 되돌아갈 수 있는지다. Retrieval score, `EvidenceRef` grounding, rejected candidate, evidence state는 03 이후의 관찰 대상이다.

## 이번 AC

1. 파싱된 PDF 본문은 page locator를 가진 `SourceUnit`으로 나뉜다.
2. `SourceUnit.text`는 실제 PDF 파싱 본문 일부이며, snippet으로 그대로 회수할 수 있다.
3. `SourceUnit`은 `material_id`, `file_name`, `page`, `unit_index`, `locator`, `text`, `search_text`를 가진다.
4. lexical search는 `SourceUnit.search_text`를 사용하되, answer evidence의 locator와 snippet은 `SourceUnit.text`로 되돌아간다.
5. embedding/vector record를 만들더라도 `source_unit_id` ref를 통해 원문으로 되돌아올 수 있다.
6. 등록되지 않은 companion source는 `SourceUnit`이나 embedding record에 섞이지 않는다.

## 구현 메모

이번 구현의 02 관찰은 `SourceUnit` retrieval까지 확인하되, public `/api/questions` 응답은 04의 `ChatAnswer` 중심 계약을 따른다. 02의 과거 smoke 응답면은 검증된 `EvidenceRef`나 fact/card 생성으로 승격하지 않는다.

- `IndexRecord`는 중간에 고려했지만 02 구현에서는 만들지 않는다. 별도 타입으로 빼면 RAG 검색 후보와 원문 `SourceUnit` boundary가 불필요하게 한 겹 더 벌어져서, lexical 검색용 text는 `SourceUnit.search_text`로 둔다.
- `EmbeddingRecord`는 유지한다. embedding은 provider, model, dimensions, vector, status 수명주기가 원문 text와 다르므로 Supabase에서도 `tripproof_source_embeddings` 테이블로 분리한다.
- 첫 개발 기본 profile은 local Ollama `nomic-embed-text-v2-moe`, 768 dimensions로 둔다. upload가 로컬 Ollama 실행 여부에 막히지 않게 provider 실패는 `EmbeddingRecord.status=failed`로 저장한다.
- auto-generate가 꺼져 있거나 provider가 없으면 `EmbeddingRecord.status`는 `pending`이다. 이 상태도 `source_unit_id`, provider, model, dimensions를 보존하므로 나중에 background job이 이어받을 수 있다.
- `RetrievalRepository`는 in-memory 구현과 Supabase adapter를 가진다. product 실행은 `TRIPPROOF_RETRIEVAL_BACKEND=supabase`일 때 Supabase `match_tripproof_source_units` RPC를 우선 사용하고, 테스트는 memory backend로 분리한다.
- local `.env`에는 실제 Supabase URL과 service role key를 둘 수 있지만, 커밋 대상은 값이 비어 있는 `.env.example`뿐이다.
- 과거 02 smoke 응답면의 `excerpt`, `excerptLocator`, `excerptSourceUnitId`는 현재 public `/api/questions` response body가 아니다. 현재 product response에서는 `QuestionResponse.answer.items[].evidence[]`의 `EvidenceRef`가 `SourceUnit` 원문으로 되돌아가는 경계를 보여준다.
- retrieval helper에는 체크인 제시물, 체크인 시작 시각, Agoda 전용 문구 같은 도메인 target 하드코딩을 넣지 않는다. query/text token과 optional vector similarity로 `RetrievedSource` 후보만 고른다.

## 구현 상태

- ready material 생성 시 `SourceUnit[]`과 `EmbeddingRecord[]`를 만든다.
- PDF 파싱 본문의 `[page N]` 마커를 읽어 page locator를 `SourceUnit`에 보존한다.
- lexical 검색은 `SourceUnit.search_text`를 쓰고, answer evidence snippet과 locator는 `SourceUnit.text`와 `SourceUnit.locator`로 되돌린다.
- embedding provider test double로 ready embedding record 생성 경로를 검증했다.
- Supabase backend profile에서는 embedding auto-generate를 시도하고, Ollama 호출 실패 시 failed embedding record를 저장한다.
- Supabase migration은 `tripproof_source_units`, `tripproof_source_embeddings`, HNSW vector index, `match_tripproof_source_units` RPC를 만든다.
- 질문 API는 retrieval repository를 통해 ready vector가 있으면 Supabase vector match 후보를, 없으면 fallback 후보를 사용해 `AnswerContext`를 만든다.
- 질문 API의 public response는 `QuestionResponse.answer` 중심이며, `SourceUnit` locator/source unit id는 `EvidenceRef.sourceUnitId`를 통해 answer evidence에 나타난다.
- 확인한 테스트: `uv run pytest apps/server/tests` 결과 24 passed. FastAPI/TestClient deprecation warning은 남아 있다.

## 남은 판단

- 첫 `SourceUnit` granularity는 현재 page 안 chunk 단위다. Agoda PDF가 길어질 때 section/문장 단위로 더 쪼갤지.
- `source_unit_id`는 현재 material id와 page/unit index 기반이다. Supabase 장기 저장 전에 content hash를 섞은 stable id로 바꿀지.
- Supabase `source_embeddings.material_id` denormalization을 DB constraint로 더 강하게 묶을지.
- Ollama 실제 호출은 설치된 embedding model과 `.env` model을 맞춘 뒤 수동 또는 integration test로 언제 검증할지.
- lexical score와 vector score를 같은 retrieval 단계에서 합칠지, 03에서 rerank나 `AnswerContext` 구성으로 넘길지.
- 03에서 `RetrievedSource`와 `EvidenceRef`를 만들 때 현재 `SourceUnitExcerpt` smoke helper를 유지할지, 03 전용 candidate 타입으로 교체할지.
