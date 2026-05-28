# TripProof Claude/Codex Bridge

이 파일은 TripProof repo의 로컬 공통 지침 원천이다.

- Claude Code는 `CLAUDE.md`를 읽는다.
- Codex는 `AGENTS.md` symlink로 같은 내용을 읽는다.
- `AGENTS.md`는 `CLAUDE.md`를 가리키는 symlink로 유지한다.
- 이 repo는 전역 skill, agent, hook, settings 정의를 복제하지 않는다.
- Claude/Codex의 tool settings, hooks, model 설정은 자동 동기화하지 않는다.
- 브릿지 상태를 점검할 때는 로컬 `bridge-auditor`를 report-only로 사용한다.
