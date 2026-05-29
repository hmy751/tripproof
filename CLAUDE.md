# TripProof Claude/Codex Bridge

이 파일은 TripProof repo의 로컬 공통 지침 원천이다.

- Claude Code는 `CLAUDE.md`를 읽는다.
- Codex는 `AGENTS.md` symlink로 같은 내용을 읽는다.
- `AGENTS.md`는 `CLAUDE.md`를 가리키는 symlink로 유지한다.
- 이 repo는 전역 skill, agent, hook, settings 정의를 복제하지 않는다.
- Claude/Codex의 tool settings, hooks, model 설정은 자동 동기화하지 않는다.
- 브릿지 상태를 점검할 때는 로컬 `bridge-auditor`를 report-only로 사용한다.

## 프로젝트 기준

- 현재 repo에서 확인 가능한 상태만 설명한다. 아직 없는 product flow, eval run, before/after 결과를 완료된 것처럼 쓰지 않는다.
- product가 먼저다. 사용자가 자료를 넣고 확인 가능한 결과를 받는 흐름을 우선 만든다.
- eval은 product behavior를 관찰한다. product가 eval fixture, run artifact, metric output에 의존하지 않게 둔다.
- 문서는 필요한 판단만 짧게 남긴다. 작은 구현 판단은 코드, commit, PR 설명 가까이에 둔다.

## Commit 규칙

- commit message는 Conventional Commits 형식을 쓴다: `type(scope): 한국어 요약`.
- `scope`는 변경 영역을 짧게 표시한다. 예: `docs`, `specs`, `client`, `server`, `shared`, `eval`, `fixtures`, `harness`.
- 제목과 본문은 기본적으로 한국어로 쓴다. type, scope, 파일명, API 이름, 명령어는 영어를 그대로 둔다.
- 여러 영역을 함께 바꾸면 가장 중심이 되는 scope를 고르고, 필요한 세부 내용은 본문에 적는다.
- 아직 구현되지 않은 product flow, eval result, proof를 완료된 것처럼 commit message에 쓰지 않는다.
