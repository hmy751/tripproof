# 2026-06-08 - Python backend와 uv ingest 경계

> 업데이트: client 실행 단위도 root `client/`로 이동했다. 현재 활성 구조는 root `client/`와 root `server/`를 나란히 둔다.

## 맥락

Agoda PDF 파일 파싱 slice에서 client-side PDF 파싱, TS normalizer, Python candidate package가 섞이면 제품의 시작점이 흐려진다. 이번 slice의 기준은 사용자가 PDF를 넣고, backend가 텍스트를 읽어 자료함과 질문 입력으로 넘기는 것이다.

## 결정

- React client는 repo root의 `client/`에 둔다.
- Python backend는 repo root의 `server/`에 둔다.
- Python 의존성과 실행환경은 `uv`와 `uv.lock`으로 관리한다.
- `pyproject.toml`은 배포용 라이브러리 패키지가 아니라 backend 앱 기준으로 둔다 (`tool.uv.package = false`).
- client는 PDF 선택과 업로드, 상태 표시만 맡고 `/api/materials`, `/api/questions`를 호출한다.
- PDF 텍스트 추출은 backend ingest가 `pypdf`로 처리한다.
- 첫 저장소는 in-memory로 둔다.
- 기존 `src/ai`, `src/server/trip-facts`, `src/shared`는 호환 계층으로 남기지 않고 삭제한다.
- LLM까지 고려한 backend 확장은 `server/extraction`, `server/llm`, `server/retrieval`을 분리한다. `extraction`은 제품 판단, `llm`은 provider 호출, `retrieval`은 chunk/search/RAG context를 맡는다.

## 기각 또는 보류

- `src/server/tripproof_server`처럼 server 하위에 다시 server를 두는 구조는 쓰지 않는다.
- `server/ai`처럼 너무 넓은 이름으로 extraction, prompt, provider, retrieval을 한데 묶지 않는다.
- TS shared contract를 억지로 유지하지 않는다. 현재 API 응답 스키마는 `server/schemas`와 client API type이 맞춘다.
- Poetry, pip-only, setuptools editable install은 이번 repo 기준으로 선택하지 않는다.
- OCR, DB, 장기 파일 저장, 실제 LLM provider 연결은 01 slice 밖이다.

## 검증

- `uv sync --frozen`
- `uv run pytest`
- `npm run build`

## 이번 결정 밖

- 02 slice의 후보 생성, evidence state, 민감정보 guard.
- backend response schema를 카드 초안과 대시보드 계약까지 확장할지.
- production storage와 파일 보존 정책.
