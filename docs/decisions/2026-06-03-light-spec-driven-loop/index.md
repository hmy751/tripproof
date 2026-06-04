# 2026-06-03 - Light spec-driven loop 운영

## 폴더 구성

- `index.md`: 결론과 현재 판단.
- `raw.md`: 이 결정이 생긴 대화, 출처 추적, 보조 에이전트 검토에서 나온 배경 재료.

`raw.md`는 현재 실행 기준이 아니다. 다음 세션은 `index.md`를 먼저 읽고, 왜 이런 결정을 했는지 필요할 때만 `raw.md`를 본다.

## 맥락

TripProof에는 spec-driven 의도가 남아 있어야 한다. 회사 요구를 product 동기로 직접 끌어오려는 것이 아니라, AI 위임을 기준 있게 관리하고 실패 유형을 product behavior로 되돌리는 역량을 보여주기 위해서다.

동시에 과거 문제는 문서, spec, eval, 하네스가 product보다 앞서면서 실행력을 약하게 만든 것이었다. 따라서 spec-driven을 repo gate나 모든 작업의 선행 절차로 복원하면 같은 문제가 반복된다.

이번 결정은 spec-driven을 없애는 결정이 아니라, TripProof에 맞는 가장 얇은 운영 루프로 낮추는 결정이다.

## 결정

TripProof의 기본 운영은 light spec-driven loop로 둔다.

- 큰 slice에만 짧은 brief를 둔다.
- brief는 `왜 지금`, `사용자 장면`, `이번 확인 기준(selected acceptance)`, `주의할 점`, `남은 판단` 정도로 제한한다.
- `selected acceptance`는 기본 1-3개로 좁힌다.
- spec은 작업을 만들지 않고, 이미 선택한 사용자 장면을 좁힌다.
- product가 먼저이고 eval은 product behavior를 관찰한다.
- AI output은 후보이며, 채택/기각은 사람이 판단한다.

큰 slice는 실패했을 때 원인과 판단이 흐려지는 작업이다. 사용자 flow 변경, 큰 AI 위임, 애매한 acceptance, 실패 유형 분해, 다음 세션 인계가 있으면 큰 slice로 본다.

작은 작업은 별도 brief나 spec 없이 진행한다. 오타, 좁은 UI 조정, 기존 acceptance 안의 bugfix, 작은 refactor, 테스트 보강은 commit, PR, test output 근처에 남긴다.

`docs/specs/README.md`에는 작업자가 바로 쓸 짧은 운영 규칙을 남긴다. 이 decision note는 왜 그 방식을 택했는지와 무엇을 기각/보류했는지를 보존한다.

`tripproof-spec-driven`은 이 repo 전용 skill로 둔다. 전역 skill이 아니라 `.claude/skills/tripproof-spec-driven`에 두고, Codex 호환은 `.codex/skills/tripproof-spec-driven` symlink로 연결한다.

## 2026-06-04 보강

spec-driven의 상단 원칙은 "구현 전에 사용자 장면, 경계, 확인 기준을 짧게 맞춰 사람과 AI가 같은 완료 조건을 보게 하는 것"으로 정리한다. 문서가 먼저 커지지 않도록, `docs/specs/README.md`와 `tripproof-spec-driven` skill은 실행용 gate가 아니라 범위 감각을 맞추는 reference로 둔다.

`docs/specs/README.md`의 권장 형식은 `한눈에 보기`와 `상세 기준`으로 나눈다.

- `한눈에 보기`: 사용자 장면, Goal, Rules, Non-goals, 상태 언어, 이번 확인 기준, 확인 방법.
- `상세 기준`: Flow, Data / State, Tests / 관찰 케이스, 보류 질문.

각 항목은 빈칸을 모두 채우는 템플릿이 아니라 다음 판단을 보정하기 위한 calibration sample로 읽는다. 예시는 "정답 양식"이 아니라 좋은/나쁜 범위 감각을 보여주는 용도다.

기존 accommodation check-in slice 문서는 현재 삭제하고, 나중에 새 권장 형식으로 다시 만든다. 이 삭제는 product flow나 첫 slice 의도를 폐기했다는 뜻이 아니라, 과거의 무거운 slice 문서가 새 light loop의 예시처럼 읽히지 않도록 비운 것이다.

`docs/specs/`의 현역 기준은 `README.md` 하나로 모은다. 과거 `00-spec-driven-development.md`는 필요한 문서 경계 원칙을 README에 얇게 흡수한 뒤 `docs/archive/spec-driven/`에 스냅샷으로 보관한다. 이는 과거 구조 판단을 삭제하려는 것이 아니라, specs 폴더 안에 두 개의 현역 기준 문서가 남아 다음 작업자나 AI가 다시 gate/queue처럼 읽는 일을 막기 위한 정리다.

## 기각 또는 보류

- 모든 작업에 spec/log/eval을 붙이는 방식은 기각한다.
- full SDD, Spec Kit, constitution, toolkit 도입은 기본값이 아니다. 여러 사람이 같은 slice를 반복 위임하거나 품질 regression이 누적될 때 별도 decision으로 다시 판단할 수 있는 이번 결정 밖의 보류 후보로 둔다.
- eval fixture, runner, metric schema를 product보다 먼저 키우는 방식은 기각한다.
- 폐기된 작업 메타나 AI 사용량 기록을 proof로 되살리는 방식은 기각한다.
- 회사 공고 키워드를 product 동기로 역수입하는 방식은 기각한다.
- TripProof 전용 skill을 글로벌 skill로 등록하는 방식은 기각한다. 이 repo 안에서만 필요한 반복 절차이므로 repo-local skill로 둔다.

## 검증

이 결정이 과해지는지는 구현 과정에서 관찰한다.

- brief가 구현을 막지 않고 시작점을 좁히는가.
- 선택한 acceptance가 1-3개로 유지되는가.
- product behavior가 먼저 생기고, eval이나 기록은 그 behavior를 관찰하는가.
- 작은 작업에 불필요한 spec/log/eval이 붙지 않는가.
- 사람이 채택/기각한 판단이 필요한 만큼만 남는가.
- `tripproof-spec-driven` skill이 큰 slice 판단과 brief 제안만 하고, 문서 gate를 만들지 않는가.

## 이번 결정 밖

- 실제 첫 slice의 UI/contract 구현 순서.
- eval run artifact 구조와 metric threshold.
- LLM adapter, ingestion, OCR, GraphRAG 같은 후속 기술 후보.
- 외부 포트폴리오 문장.
