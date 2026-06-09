# 2026-06-09 - 구현 노트 기록 위치 신설

## 맥락

TripProof에는 이미 `docs/decisions/`, `docs/work-log.md`, `docs/specs/`가 있다. 하지만 구현 중 반복해서 드러나는 오해, drift, 경계 관찰은 세 위치 중 어디에도 자연스럽게 맞지 않았다.

- `docs/decisions/`는 채택/기각/보류한 구조적 선택을 남긴다.
- `docs/work-log.md`는 다음 세션 재진입을 돕는 얇은 과거 기록이다.
- `docs/specs/`는 여러 작업으로 이어지는 제품 동작 기준과 AC를 둔다.

구현 중 발생한 "다음에도 같은 경계를 조심해야 한다"는 관찰은 결정도, 재진입 로그도, 제품 기준도 아니다. 그래도 나중에 모아볼 가치가 있으면 repo 안에 독립적인 위치가 필요했다.

## 결정

`docs/implementation-notes/`를 구현 중 오해, drift, 경계 관찰을 남기는 별도 위치로 둔다.

이 폴더의 본질은 진행 상황이나 대화 원문을 보존하는 것이 아니라, 비슷한 구현에서 다시 헷갈릴 수 있는 경계를 짧은 calibration sample로 남기는 것이다.

함께 둔 기준:

- `docs/implementation-notes/README.md`: 구현 노트의 역할, 좋음/나쁨, 판단 질문, 냄새 신호.
- `.claude/skills/implementation-note`: 현재 대화/작업 세션에 남길 구현 노트가 있는지 판단하고, 너무 약하거나 다른 위치가 맞으면 저장하지 않는 skill.
- `.codex/skills/implementation-note`: Codex 호환 symlink.

## 기각 또는 보류

- **개별 구현 경계 관찰을 `docs/decisions/`에 남기기 - 기각.** 결정으로 승격하면 작은 drift 관찰까지 구조적 선택처럼 보일 수 있다.
- **개별 구현 경계 관찰을 `docs/work-log.md`에 누적하기 - 기각.** work-log가 재진입 기록이 아니라 장기 판단 노트가 된다.
- **개별 구현 경계 관찰을 `docs/specs/`에 넣기 - 기각.** spec이 제품 동작 기준보다 구현 중 오해 기록을 품게 된다.
- **개인 `ai-note`에만 남기기 - 기각.** 개인 학습 관찰로는 유효하지만, TripProof repo 안에서 반복 구현 경계를 다시 보기 어렵다.

## 검증

- `docs/implementation-notes/README.md`가 "진행 기록이 아니라 반복될 경계 오해를 calibration sample로 남기는 자리"라는 원칙을 먼저 밝힌다.
- `docs/decisions/README.md`, `docs/development-notes.md`, `docs/work-log.md`, `CLAUDE.md`가 새 기록 위치를 가리킨다.
- `spec-driven` skill은 기록 위치 목록에 `docs/implementation-notes/*.md`만 알고, 실제 저장 판단은 `implementation-note` skill이 맡는다.
- `public-doc-wording-reviewer`는 `docs/implementation-notes/**/*.md`도 공개 문서 톤 점검 대상으로 본다.

## 이번 결정 밖

- 특정 구현 사건을 바로 노트로 남길지 여부.
- `docs/implementation-notes/`의 첫 실제 노트 내용.
- 구현 노트를 PR/commit 템플릿과 연결하는 운영.
