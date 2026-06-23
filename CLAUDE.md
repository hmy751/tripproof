# TripProof Claude/Codex Bridge

이 파일은 TripProof repo의 로컬 공통 지침 원천이다.

- Claude Code는 `CLAUDE.md`를, Codex는 이를 가리키는 `AGENTS.md` symlink를 읽는다. 두 도구가 같은 내용을 본다. `AGENTS.md`는 일반 파일로 바꾸지 말고 symlink로 유지한다.
- 이 repo는 전역 skill, agent, hook, settings 정의를 복제하지 않는다.
- 이 repo의 반복 작업에만 필요한 skill은 repo-local `.claude/skills/`에 둔다. Codex 호환이 필요하면 `.codex/skills/`에서 같은 skill을 symlink한다.
- `spec-driven`은 TripProof 전용 light spec-driven 작업 루프다. spec/AC/product contract가 현재 작업의 판단 기준일 때 사용한다.
- `implementation-note`는 구현 중 반복해서 다시 볼 오해, drift, 경계 관찰을 `docs/implementation-notes/`에 남길지 판단할 때 사용한다. 너무 약하거나 다른 기록 위치가 맞으면 저장하지 않고 이유를 말한다.
- Claude/Codex의 tool settings, hooks, model 설정은 자동 동기화하지 않는다.
- 브릿지 파일(CLAUDE.md/AGENTS.md, skill symlink, agent pair)을 수정한 뒤에는 로컬 `bridge-auditor`를 report-only로 점검한다.

## 프로젝트 기준

- 현재 repo에서 확인 가능한 상태만 설명한다. 아직 없는 product flow, eval run, before/after 결과를 완료된 것처럼 쓰지 않는다.
- product가 먼저다. 사용자가 자료를 넣고 확인 가능한 결과를 받는 흐름을 우선 만든다.
- eval은 product behavior를 관찰한다. product가 eval fixture, run artifact, metric output에 의존하지 않게 둔다.
- 문서는 필요한 판단만 짧게 남긴다. 작은 구현 판단은 코드, commit, PR 설명 가까이에 둔다.
- 구현 중 반복해서 다시 볼 오해, drift, 경계 관찰은 decision이나 work-log로 억지 승격하지 않고 `docs/implementation-notes/`에 둔다.
- `docs/decisions/`, `docs/implementation-notes/`, `docs/work-log.md`처럼 대화 세션, 판단 과정, AI/subagent 검토 흔적이 들어갈 수 있는 문서를 새로 쓰거나 크게 고친 뒤에는 `public-doc-wording-reviewer`를 report-only로 실행한다. 이 agent는 승인 gate가 아니라 private source 누수와 공개 문서 독립성을 점검하는 마지막 확인이다. 실행하지 않으면 이유를 짧게 남긴다.
- 하네스와 문서는 실행을 돕는 기준이지 현재 작업 승인권이 아니다. 과거 분석, roadmap, work-log, subagent report를 그대로 다음 명령으로 승격하지 않는다.
- 삭제, 스택 전환, shared 계약 변경, legacy 제거, commit/stage처럼 되돌리기 비용이 큰 변경은 먼저 사용자에게 알린다. 이미 합의된 slice 안의 작은 UI, 함수, 스타일, 타입 정리는 멈춰 묻기보다 진행하고 결과로 설명한다. 어느 쪽인지 애매하면 되돌리기 비용이 큰 쪽으로 간주하고 먼저 알린다.
- subagent와 로컬 agent는 판단 재료를 제공하는 report-only 도구다. 승인/반려 권한은 갖지 않는다.
- 사용자가 "두고", "멈춰", "보류"라고 말하면 파일 수정과 추가 실행을 멈추고 현재 상태를 보고한다.

## 검증과 포맷

- Python 포맷터는 Black을 기준으로 한다. 설정은 `pyproject.toml`의 `[tool.black]`과 `black` dev dependency를 원천으로 둔다.
- Python 포맷 실행은 `npm run black` 또는 `npm run format`을 사용한다.
- Python 포맷 검증은 `npm run black:check` 또는 `npm run format:check`를 사용한다.
- 검증은 현재 변경의 목적에 맞게 고른다. 코드 형식, 타입, 단위 테스트, product/eval 실행은 서로 다른 확인이다.
- 자료 QA, LLM, retrieval, eval 질문셋을 다룰 때는 단순 형식/단위 테스트 통과를 product behavior 통과로 말하지 않는다. 실제 자료 입력과 질문 실행 결과를 별도로 확인한다.

## Commit 규칙

- commit message는 Conventional Commits 형식을 쓴다: `type(scope): 한국어 요약`.
- `scope`는 변경 영역을 짧게 표시한다. 예: `docs`, `specs`, `client`, `server`, `shared`, `eval`, `fixtures`, `harness`.
- 제목과 본문은 기본적으로 한국어로 쓴다. type, scope, 파일명, API 이름, 명령어는 영어를 그대로 둔다.
- 여러 영역을 함께 바꾸면 가장 중심이 되는 scope를 고르고, 필요한 세부 내용은 본문에 적는다.
- 아직 구현되지 않은 product flow, eval result, proof를 완료된 것처럼 commit message에 쓰지 않는다.

## 코드 변경 원칙

- 코드를 설계하거나 변경할 때는 `docs/engineering/`(`principle.md` / `architecture.md` / `testing.md` / `ai-coding.md`)을 기준으로 삼는다.
- 제품 동작의 강제는 테스트가 맡고, 이 문서는 테스트로 잡기 어려운 설계·구조·실패 판단을 정할 때 보는 기준이다.
