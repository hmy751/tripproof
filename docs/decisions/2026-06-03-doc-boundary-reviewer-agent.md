# 2026-06-03 - 문서 경계 검토 에이전트 추가

## 맥락

TripProof는 숙소 체크인 자료를 사용자가 넣으면, AI가 그 자료에서 확인 가능한 체크인 정보를 정리해 주는 제품 slice를 만들고 있다.

이 repo에는 의도적으로 spec-driven, slice, harness 성격의 문서가 들어왔다. 이는 제품 기준, 작업 단위, AI-assisted 개발 흐름을 추적 가능하게 남기기 위한 선택이었다.

문제는 spec-driven 자체가 아니다. 문제는 문서가 많아지면서 일부 문장이 제품 기준이 아니라 "다음에는 이 순서로 해라", "이 후보를 처리해라", "이 분석을 따라라" 같은 현재 작업 명령처럼 읽힐 수 있다는 점이었다. 그러면 다음 AI는 사용자의 최신 의도나 현재 코드 상태보다 과거 문서의 절차를 더 강하게 따르게 된다.

따라서 필요한 것은 문서를 더 정교한 절차로 만드는 일이 아니라, 문서가 어떤 역할을 해야 하는지 구분하는 점검 장치다.

- 제품 기준은 남긴다.
- spec, slice, harness가 주는 구조와 추적 가능성도 남긴다.
- 다만 과거 분석, 작업 후보, 실행 순서, 문서 운영 절차가 현재 명령처럼 굳지 않게 한다.

## 결정

TripProof 로컬 agent로 `doc-boundary-reviewer`를 추가한다.

- Claude용 정의: `.claude/agents/doc-boundary-reviewer.md`
- Codex용 정의: `.codex/agents/doc-boundary-reviewer.toml`

이 agent는 문서 수정안이 제품 판단을 보존하는 기준인지, 아니면 다음 작업을 지휘하는 절차, queue, gate로 굳는지 report-only로 점검한다. 직접 파일을 수정하지 않고, 승인/반려 권한도 갖지 않는다.

핵심은 파일 목록 점검이 아니라 판단 감각이다. 문서 위치나 제목보다 문장이 만드는 행동 권한을 본다.

좋은 문서의 예:

- `docs/product-model.md`가 TripProof의 객체, 상태, chat-first 흐름을 한 번만 설명한다.
- `docs/specs/`가 여러 작업으로 이어질 product behavior acceptance를 짧게 남긴다.
- work log가 이미 바뀐 것과 남은 관찰을 기록하되, 다음 작업 queue처럼 쓰이지 않는다.

위험한 문서의 예:

- 과거 분석 결과가 "현재 따라야 할 결론"처럼 쓰인다.
- fixture나 roadmap 문서가 제품 구현보다 먼저 AI의 실행 순서를 지휘한다.
- README나 CLAUDE.md가 문서 운영 규칙표처럼 커져 항상 켜지는 gate가 된다.

## 기각 또는 보류

- 모든 문서 수정 전에 agent를 반드시 실행하는 방식은 기각한다. 그 자체가 새 gate가 된다.
- agent 결과를 승인/반려 판정으로 쓰는 방식은 기각한다. 결과는 판단 재료일 뿐이다.
- 이 기준을 `README.md`나 `CLAUDE.md`에 길게 풀어 쓰는 방식은 보류한다. 항상 켜지는 문서가 다시 운영 규칙표처럼 커질 수 있다.
- 전역 agent로 승격하는 것은 보류한다. 현재 기준은 TripProof 문서 구조와 이번 논의에 특화되어 있다.

## 검증

- `AGENTS.md`는 계속 `CLAUDE.md` symlink로 남아 있고, 로컬 agent pair만 추가했다.
- Codex agent는 `sandbox_mode = "read-only"`를 둔다.
- 두 agent 모두 `Report-only`, `Never edit`, `승인/반려하지 않는다`, `필수 gate가 아니다`를 명시한다.
- Claude/Codex agent pair는 같은 역할과 제한을 유지하도록 맞췄다.

## 남은 관찰

- 이 agent는 문서 수정의 필수 단계가 아니다. 호출된 경우에도 위험과 이유, 최소 패치 후보만 보고한다.
- 실제 문서 수정 판단은 사용자 의도와 현재 코드 상태를 함께 보며 main 대화에서 닫는다.
- 이 결정은 agent 추가에 관한 기록이다. TripProof 문서 개편 전체를 승인하거나, 특정 문서를 archive로 보내기로 확정한 결정은 아니다.
