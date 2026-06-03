# Raw Notes - 하네스 문서 역할 재정렬

이 파일은 `index.md` 결정의 배경을 보존하는 raw note다. 현재 실행 기준이 아니라, 다음 세션이 왜 이 결정을 했는지 빠르게 체감하기 위한 자료다.

## 대화에서 드러난 문제 감각

사용자는 TripProof 작업이 slice 기반으로 진행되지 않고 계속 발목 잡힌다고 봤다. 처음에는 하네스 자체가 문제처럼 보였지만, 대화가 이어지며 결론은 더 좁아졌다.

- 하네스의 존재 자체가 문제는 아니다.
- 문제는 하네스의 활용 방식과 표현 방식이다.
- 문서를 "수정/보완"하라고 하면 AI가 삭제·교정·격리 대신 새 규칙을 덧대는 경향이 있다.
- 그렇게 덧댄 문장은 다시 다음 AI에게 후보, 근거, 금지 규칙, 작업 대기열처럼 재호출된다.
- 해결되지 않은 문제에서는 생각이 열리는 것이 자연스럽다. 답은 "생각을 닫자"가 아니라, 문서가 열린 생각을 현재 명령으로 오해하지 않게 하는 것이다.

사용자가 특히 경계한 것은 "하지 말자"를 또 다른 산출물로 만드는 흐름이었다. 개발로 비유하면 잘못된 값을 제거하거나 구조를 고치는 대신 하드코딩 예외를 계속 추가하는 것과 비슷하다.

## 외부 하네스 조사에서 나온 5개 패턴

### 1. `CLAUDE.md` / `AGENTS.md`는 현재 명령서가 아니라 orientation이다

외부 사례 맥락:

- OpenAI Codex `AGENTS.md`는 agent가 작업 전에 읽는 instruction discovery 체계다.
- AGENTS.md convention은 agent용 README에 가까운 공통 포맷을 지향한다.
- GitHub Copilot repository instruction도 repository-wide context 성격이 강하다.

TripProof에 비춘 해석:

- 항상 켜지는 문서가 현재 task queue가 되면 사용자 최신 요청보다 과거 문서가 앞에 선다.
- 그래서 `CLAUDE.md` / `AGENTS.md`는 제품 spec이나 과거 분석을 담지 않는 얇은 실행 경계로 낮춘다.

### 2. 항상 켜지는 instruction은 짧고 넓게 둔다

외부 사례 맥락:

- Cursor, Continue, Cline, GitHub Copilot은 repo-wide rule과 scoped/on-demand rule을 나누는 방향을 가진다.
- OpenHands는 permanent context와 on-demand skills를 나눠 progressive disclosure를 지향한다.

TripProof에 비춘 해석:

- root 문서에 세부 운영 규칙을 계속 넣으면 또 다른 anchor가 된다.
- 지금은 새 rule 구조를 만들기보다 문서별 역할을 낮추고, 세부 판단은 해당 문서나 현재 작업 가까이에 둔다.

### 3. 자연어 instruction과 실제 enforcement를 분리한다

외부 사례 맥락:

- Claude Code hooks, OpenHands hooks, CI/test는 실제로 막거나 실행되는 계층이다.
- 자연어 instruction은 작업자에게 맥락과 판단 기준을 준다.

TripProof에 비춘 해석:

- 이 항목이 이번 문제와 가장 직접 연결된다.
- TripProof에는 실제 enforcement가 거의 없었다. 그래서 자연어 문서가 사실상 유일한 "강제 장치"처럼 작동했다.
- roadmap/spec/work-log의 후보 문장이 다음 AI에게 실행 queue나 approval authority처럼 읽혔다.
- 문제는 enforcement가 너무 강한 것이 아니라, enforcement가 없는 상태에서 자연어 문서가 enforcement 역할까지 떠안은 것이다.

결론:

- 문서가 실제 gate인 척하지 않게 한다.
- 실제 gate가 필요하면 test/CI/hook/permission 위치에서 좁게 만든다.
- 자연어 문서는 판단 기준과 맥락으로 남긴다.

### 4. 조사·계획과 실행 권한을 분리한다

외부 사례 맥락:

- Continue Plan Mode는 read-only 계획과 실행을 분리한다.
- Aider는 `CONVENTIONS.md` 같은 문서를 read-only context로 넣을 수 있다.
- Claude subagent는 별도 context와 제한된 tool access로 bounded task를 맡는다.

TripProof에 비춘 해석:

- subagent 결과가 "팀이 봤으니 승인"처럼 되면 main 판단이 흐려진다.
- `doc-boundary-reviewer`, `anchor-expression-reviewer`는 report-only로만 둔다.
- 조사 결과는 decision의 재료이지 실행 승인권이 아니다.

### 5. eval/spec은 product behavior를 관찰한다

외부 사례 맥락:

- eval은 workflow/result를 관찰하고 trace/metric으로 실패를 드러내는 장치다.
- BDD와 test 관행도 concrete behavior를 확인하는 데 의미가 있다.

TripProof에 비춘 해석:

- spec과 fixture가 product보다 앞서면 사용자가 보는 흐름 대신 하네스 통과가 목표가 된다.
- 그래서 spec은 product behavior acceptance로 두고, eval은 product code를 호출해 관찰한다.
- product가 eval fixture, run artifact, metric output에 의존하지 않는다.

## 이번 대화에서 추가로 정리된 판단

사용자는 "겹친다고 그냥 두지 말고 자료가 어떤 맥락이고 우리 것과 비교해서 무엇을 추가하거나 개선해도 좋을지 보라"고 했다.

검토 결과:

- 1, 2, 4, 5는 이미 현재 문서에 꽤 반영되어 있다.
- 3은 부분 반영이었다. `CLAUDE.md`에 hooks/settings를 복제하지 않는다는 경계는 있었지만, 자연어 instruction과 실제 enforcement를 어떻게 구분해 읽을지는 한 번 더 명확히 할 필요가 있었다.
- `CLAUDE.md`에 새 문장을 넣으면 항상 켜지는 anchor가 늘어난다. 그래서 3번은 decision note에만 남긴다.
- `## 다음` 같은 heading은 decision 안에서 새 queue처럼 읽힐 수 있어 `## 이번 결정 밖`으로 낮춘다.
- `work-log`의 "그 뒤 MVP 흐름" 같은 약한 순서 표현도 현재 작업 지시처럼 읽히지 않게 낮춘다.

## 반영하지 않은 것

- 새 `.clinerules`, `.continue/rules`, path-scoped rule 구조를 만들지 않는다.
- 모든 문서 수정 전에 `doc-boundary-reviewer`나 `anchor-expression-reviewer`를 필수로 돌리지 않는다.
- 외부 레퍼런스를 권위로 세우지 않는다.
- transcript나 raw note를 현재 실행 기준으로 승격하지 않는다.

## 재진입 메모

다음 세션이 이 결정을 읽을 때 핵심은 아래 한 문장이다.

> TripProof의 문제는 하네스가 있어서가 아니라, 자연어 문서가 context, 판단 기준, 과거 기록, 작업 대기열, 실제 gate 역할을 한꺼번에 떠안으면서 현재 실행 권한처럼 읽힌 것이다.

따라서 다음 문서 수정은 규칙 추가부터 하지 말고, 대상이 삭제·교정·격리·보완 중 무엇인지 먼저 본다. 그리고 실제로 강제해야 하는 것은 문장이 아니라 test, CI, hook, permission 같은 장치가 생겼을 때 좁은 위치에서 다룬다.
