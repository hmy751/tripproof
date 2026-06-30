# TripProof Claude/Codex Bridge

이 파일은 TripProof repo의 로컬 공통 지침 원천이다.

## 브릿지와 repo-local 도구

- Claude Code는 `CLAUDE.md`를, Codex는 이를 가리키는 `AGENTS.md` symlink를 읽는다. 두 도구가 같은 내용을 본다.
- `AGENTS.md`는 일반 파일로 바꾸지 말고 symlink로 유지한다.
- 이 repo는 전역 skill, agent, hook, settings 정의를 복제하지 않는다.
- 이 repo의 반복 작업에만 필요한 skill은 repo-local `.claude/skills/`에 둔다. Codex 호환이 필요하면 `.codex/skills/`에서 같은 skill을 symlink한다.
- `spec-driven`은 TripProof 전용 light spec-driven 작업 루프다. spec/AC/product contract가 현재 작업의 판단 기준일 때 사용한다.
- `implementation-note`는 구현 중 반복해서 다시 볼 오해, drift, 경계 관찰을 `docs/implementation-notes/`에 남길지 판단할 때 사용한다. 너무 약하거나 다른 기록 위치가 맞으면 저장하지 않고 이유를 말한다.
- Claude/Codex의 tool settings, hooks, model 설정은 자동 동기화하지 않는다.
- 브릿지 파일(CLAUDE.md/AGENTS.md, skill symlink, agent pair)을 수정한 뒤에는 로컬 `bridge-auditor`를 report-only로 점검한다.

## 프로젝트 기준

- 현재 repo에서 확인 가능한 상태만 설명한다. 아직 없는 product flow, eval run, before/after 결과를 완료된 것처럼 쓰지 않는다.
- product가 먼저다. 사용자가 자료를 넣고 확인 가능한 결과를 받는 흐름을 우선 만든다.
- eval은 product behavior를 관찰한다. product가 eval fixture, run artifact, metric output에 의존하지 않게 둔다. 이 경계의 단일 기준은 `docs/engineering/architecture.md`다.
- 문서는 필요한 판단만 짧게 남긴다. 작은 구현 판단은 코드, commit, PR 설명 가까이에 둔다.
- 구현 중 관찰은 decision이나 work-log로 억지 승격하지 않고 `docs/implementation-notes/`에 둔다.

## 코드 변경 원칙

`docs/engineering/`은 TripProof의 engineering 판단 기준이다 — 제품 동작의 강제는 테스트가 맡고, 이 문서는 테스트가 못 잡는 설계 판단을 든다.

@docs/engineering/README.md
<!-- Claude는 위 줄로 README(판단 기준 인덱스)를 세션 시작 시 강제 로드(import)한다.
     Codex는 import 구문을 해석하지 않으니 아래 라우터를 직접 보고 해당 문서를 기준으로 읽는다. (의도된 비대칭) -->

- 파일을 수정하거나 설계를 새로 잡기 전 짧게 판단한다: 이 변경이 product behavior, architecture boundary, eval/product 분리, shared API, retrieval/LLM behavior, persistence, testing strategy, AI coding workflow, 삭제/마이그레이션/큰 refactor를 건드리는가?
- 아니라면 주변 코드 패턴과 관련 테스트를 우선한다. 하나라도 해당하면 그 경계 문서를 기준으로 삼는다:
  - product/eval/architecture boundary·의존 방향 → `architecture.md`
  - 구조·추상화 시점·관심사 경계·실패 정책 → `principle.md`
  - 동작을 무엇으로 확인하나(테스트·fixture·eval 해석) → `testing.md`
  - LLM을 제품에 넣는 출력/계약 설계 → `llm-design.md` ⚠ 자주 틀림: code는 의미 role을 발명하지 않는다(있냐없냐만) — 의미 분류는 LLM/relation extractor, 승격은 code
  - AI에게 코드를 맡길 때의 경계 → `ai-coding.md`
  - formatter와 review 책임 구분 → `code-style.md`
- cross-cutting 변경이나 되돌리기 비용이 큰 변경에서는 `docs/engineering/` 전체를 확인한다.
- 사용자가 준 reading list는 우선 context이지, repo 기준을 배제하는 닫힌 목록이 아니다.

## 권한과 중단

- 하네스와 문서는 실행을 돕는 기준이지 현재 작업 승인권이 아니다. 과거 분석, roadmap, work-log, subagent report를 그대로 다음 명령으로 승격하지 않는다.
- 삭제, 스택 전환, shared 계약 변경, legacy 제거, commit/stage처럼 되돌리기 비용이 큰 변경은 먼저 사용자에게 알린다. 이미 합의된 slice 안의 작은 UI, 함수, 스타일, 타입 정리는 멈춰 묻기보다 진행하고 결과로 설명한다. 어느 쪽인지 애매하면 되돌리기 비용이 큰 쪽으로 간주하고 먼저 알린다.
- subagent와 로컬 agent는 판단 재료를 제공하는 report-only 도구다. 승인/반려 권한은 갖지 않는다.
- 사용자가 "두고", "멈춰", "보류"라고 말하면 파일 수정과 추가 실행을 멈추고 현재 상태를 보고한다.
- product-first나 자율 진행과 충돌하면, 사용자의 명시적 멈춤을 항상 우선한다.

## 검증과 포맷

- Python 포맷터는 Black을 기준으로 한다. 설정은 `pyproject.toml`의 `[tool.black]`과 `black` dev dependency를 원천으로 둔다.
- Python 포맷 실행은 `npm run black` 또는 `npm run format`을 사용한다.
- Python 포맷 검증은 `npm run black:check` 또는 `npm run format:check`를 사용한다.
- client(React/Vite)는 `npm run client:typecheck`와 `npm run client:build`로 확인한다. server 포맷·client 빌드·test를 한 번에 보려면 `npm run check`를 쓴다.
- 검증은 현재 변경의 목적에 맞게 고른다. 코드 형식, 타입, 단위 테스트, product/eval 실행은 서로 다른 확인이다.
- 자료 QA, LLM, retrieval, eval 질문셋을 다룰 때는 단순 형식/단위 테스트 통과를 product behavior 통과로 말하지 않는다. 실제 자료 입력과 질문 실행 결과를 별도로 확인한다.
- `docs/decisions/`, `docs/implementation-notes/`, `docs/work-log.md`처럼 대화 세션, 판단 과정, AI/subagent 검토 흔적이 들어갈 수 있는 문서를 새로 쓰거나 크게 고친 뒤에는 `public-doc-wording-reviewer`를 report-only로 실행한다. 이 agent는 승인 gate가 아니라 private source 누수와 공개 문서 독립성을 점검하는 마지막 확인이다. 실행하지 않으면 이유를 짧게 남긴다.

## Branch 규칙

- branch 이름은 `<kind>/<kebab-case-subject>`를 쓴다.
- `kind`는 작업 성격을 나타낸다: `feat`, `fix`, `refactor`, `spec`, `eval`, `docs`, `chore`.
- subject는 모듈명보다 product slice, 관찰된 실패 유형, architecture boundary를 우선한다. 예: `feat/agoda-pdf-source-units`, `fix/certification-keyword-gate`, `refactor/server-use-cases`, `spec/agoda-original-pdf-qa-improvement`, `eval/question-runtime-recording`.
- AI 도구명, 작업자명, 개인 실행 환경 이름은 branch prefix로 쓰지 않는다.
- `feature`는 `feat`와 중복되므로 새 branch에서는 쓰지 않는다. repo 운영·브릿지·스크립트 정리는 보통 `chore`, product contract 문서는 `spec`, 일반 판단 문서는 `docs`를 쓴다.
- 백업·임시 통합 branch는 공유 컨벤션으로 올리지 않고, 필요할 때만 목적과 날짜가 드러나게 만든다.

## Commit 규칙

- commit message는 Conventional Commits 형식을 쓴다: `type(scope): 한국어 요약`.
- `scope`는 변경 영역을 짧게 표시한다. 예: `docs`, `specs`, `client`, `server`, `shared`, `eval`, `fixtures`, `harness`.
- 제목과 본문은 기본적으로 한국어로 쓴다. type, scope, 파일명, API 이름, 명령어는 영어를 그대로 둔다.
- 여러 영역을 함께 바꾸면 가장 중심이 되는 scope를 고르고, 필요한 세부 내용은 본문에 적는다.
- 아직 구현되지 않은 product flow, eval result, proof를 완료된 것처럼 commit message에 쓰지 않는다.
