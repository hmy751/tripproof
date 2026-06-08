# 2026-06-08 - Python backend와 uv ingest 경계

## 맥락

Agoda PDF 파일 파싱 slice에서 client-side PDF 파싱, TS normalizer, Python candidate package가 섞이면 제품의 시작점이 흐려진다. 이번 slice의 기준은 사용자가 PDF를 넣고, backend가 텍스트를 읽어 자료함과 질문 입력으로 넘기는 것이다.

## 결정

- Python backend는 repo root의 `server/`에 둔다.
- Python 의존성과 실행환경은 `uv`와 `uv.lock`으로 관리한다.
- `pyproject.toml`은 배포용 라이브러리 패키지가 아니라 backend 앱 기준으로 둔다 (`tool.uv.package = false`).
- client는 PDF 선택과 업로드, 상태 표시만 맡고 `/api/materials`, `/api/questions`를 호출한다.
- PDF 텍스트 추출은 backend ingest가 `pypdf`로 처리한다.
- 첫 저장소는 in-memory로 둔다.
- 기존 `src/ai`, `src/server/trip-facts`, `src/shared`는 호환 계층으로 남기지 않고 삭제한다.

## 기각 또는 보류

- `src/server/tripproof_server`처럼 server 하위에 다시 server를 두는 구조는 쓰지 않는다.
- TS shared contract를 억지로 유지하지 않는다. 현재 API 응답 스키마는 `server/models.py`와 client API type이 맞춘다.
- Poetry, pip-only, setuptools editable install은 이번 repo 기준으로 선택하지 않는다.
- OCR, DB, 장기 파일 저장, LLM provider 연결은 01 slice 밖이다.

## 검증

- `uv sync --frozen`
- `uv run pytest`
- `npm run build`

## 이번 결정 밖

- 02 slice의 후보 생성, evidence state, 민감정보 guard.
- backend response schema를 카드 초안과 대시보드 계약까지 확장할지.
- production storage와 파일 보존 정책.
