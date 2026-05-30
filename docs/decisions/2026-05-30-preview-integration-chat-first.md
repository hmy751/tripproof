# 2026-05-30 - Preview 통합 / chat-first 채택 / 상태 2축 확정

## 맥락

TripProof에는 두 갈래의 제품 서술이 있었다. `docs/`(prd.md, specs/accommodation-checkin.md)는 moment-first 흐름(여행 순간 선택 → 자료 → 질문 → 상황 카드)으로 제품을 그렸고, 채팅(질의응답)을 Later Feature로 미뤘다. 이후 추가된 `docs/archive/preview/`(prd.md, tripproof-preview-c.html)는 chat-first 경험(자료함 채팅 1차, 인라인 근거, 일정×카테고리 대시보드, 현장 카드, 근거 부족해도 직접 채워 올리기)을 그렸다.

사용자는 preview의 제품 감각·UX를 더 선호하고, 기존 docs를 지나치게 따르지 말라고 명시했다. 다만 AI 기능(추출·근거·근거 부족·충돌·민감정보 처리)은 "또 다른 문제"라고 짚었다 — preview의 가벼운 서술로 뭉갤 영역이 아니라는 뜻이다. 두 서술이 한 repo 안에서 충돌한 채로 남으면 이후 모든 문서·구현 판단이 흔들린다. 그래서 단일 통합 모델 기준 문서가 필요했다.

추가로, `docs/archive/preview/prd.md`의 Information States 표(line 225-234)는 근거 상태(supported/needs_review/missing/conflict)와 사람이 결정한 카드 출처(user=직접 확인, saved=현장 저장)를 한 표에 섞었다. preview 스스로 line 234에서 두 축의 직교성을 인정하고 있었다.

## 결정

1. **레이어 소유로 통합한다 (preview냐 docs냐를 전역에서 고르지 않는다).** 인터랙션·UX·화면 흐름은 preview가 리드하고, AI 기능·요구·엄밀함은 docs가 지킨다. 제품·UX·인터랙션이 충돌하면 preview를 채택하지만, acceptance·AI behavior·도메인 타입·eval 축은 docs를 보존한다.

2. **chat-first 채택.** moment-first 입구와 '채팅=Later Feature' 프레이밍은 버리고 chat-first로 재서술한다. moment 개념은 카드의 '일정(타임라인)' 분류로만 잔존한다. slice는 도메인을 좁히는 것이지 인터랙션을 미루는 게 아니다 — 첫 slice(숙소 체크인)도 chat-first 흐름을 끝까지 통과시킨다.

3. **단일 기준 문서.** `docs/product-model.md`를 통합 모델 기준 문서로 두고, 이후 모든 제품 문서가 이 기준 문서의 어휘·상태·흐름을 그대로 쓴다. 개념·가치는 기준 문서에서 한 번만 서술하고, PRD/spec/README는 참조한다.

4. **상태 2축 확정.** 한 표를 두 직교 축으로 분리한다. 근거 축 EvidenceState(supported/needs_review/missing/conflict, 답변 레벨)와 결정 축 ReviewDecision/카드 출처(근거 그대로 올림/직접 확인/무시/현장 저장, 카드 레벨). 사용자-facing 문구 6개(근거 있음/확인 필요/근거 부족/자료 충돌/직접 확인/현장 저장)는 preview 그대로 보존하되 올바른 축에 배치한다. 2축 분리는 preview를 부정하는 게 아니라, preview가 line 234에서 이미 인정한 직교성을 명시적 구조로 만든 것이다.

5. **어휘 통일.** '직접 확인'이 옛 docs에서 needs_review 번역어이자 `marked_for_review`로 과부하됐다. '확인 필요'=needs_review(근거 축, 답변 레벨), '직접 확인'=사람이 채운 카드 출처(결정 축, 카드 레벨)로 분리 고정한다. 옛 `ReviewDecision`의 4값(saved/edited_and_saved/ignored/marked_for_review)을 그대로 쓰지 않는다 — `marked_for_review`는 폐기하고(답변 레벨 needs_review로 흡수), `saved`의 의미는 '저장됨'에서 '현장 저장(field card)'으로 재정의한다. 충돌 명사(상황 카드↔대시보드, 여행 순간↔일정/채팅)도 preview 용어로 통일한다.

## 기각 또는 보류

- moment-first 입구(여행 순간을 먼저 선택)는 기각한다. chat-first와 충돌하고, 사용자가 preview를 선호한다.
- '상황 카드(SituationCard)'라는 단일 종착점 명사는 기각한다. 일정×카테고리 대시보드 + 현장 카드 2단계로 대체한다.
- 채팅을 Later Feature로 두는 프레이밍은 기각한다. 채팅이 주 인터랙션이다.
- AI confidence 수치를 사용자 언어로 쓰는 것은 기각한다(preview의 명시적 나쁜 표현).
- 코드 수정은 보류한다. 이번 통합은 문서만 바꾼다. 공유 타입 확장(value:string|null, category, ReviewDecision)은 구현 slice에서 별도 판단한다.

## 검증

- `src/shared/tripFacts.ts` 실제 타입을 읽어 기준 문서 매핑을 맞췄다. 확인: EvidenceState 4값은 코드와 일치. `TripFact.value`는 현재 `string`(코드), slice spec은 `string|null` 확장 필요를 이미 지적. category/reviewDecision/conflictCandidates/reason은 코드에 없음 → 확장 후보로 명시.
- `docs/archive/preview/tripproof-preview-c.html`의 confirmDraft 로직이 결정 축을 실제로 구현함을 확인: 근거 없는 카드 또는 supported인데 사람이 값·이름을 고친 카드를 state='user'(직접 확인)로 바꾼다. 기준 문서의 출처를 바꾸는 규칙은 preview 동작에 근거한다.
- docs/archive/preview/prd.md line 234가 두 축의 직교성을 이미 인정함을 확인.
- 통합 초안을 콘텐츠 손실 / 정직성·CLAUDE.md 준수 / preview 충실도 3개 렌즈로 적대적 검증했고, 셋 다 pass_with_fixes(needs_rework 없음). 지적된 fix(타입 계약 목표/현재 분리 표기, 탭 위계 명시, 결정 축 supported origin 직교성 주석, 문구 나열 순서 통일)는 최종 문서에 반영했다.

## 다음

- 이 통합은 기준 문서(`docs/product-model.md`)·결정 노트·`docs/prd.md`·`docs/specs/accommodation-checkin.md` 정렬과 `docs/archive/preview/prd.md` 배너·`README.md`·`docs/specs/00-spec-driven-development.md` 색인을 **한 변경 단위로** 적용한다. README/spec 색인이 product-model.md를 참조하므로, 기준 문서 파일 생성과 같은 단위가 아니면 dangling reference가 된다.
- `docs/development-notes.md`(product/eval 기본 방향 노트)는 유지한다. 흐름 서술이 기준 문서와 겹치면 기준 문서를 참조하도록 정리하는 것은 별도 후보.
- 코드 드리프트 follow-up(문서만으로는 닫지 않음, 구현 slice에서 판단):
  - `TripFact.confidence: number`가 코드에 있으나 사용자 언어로 쓰지 않기로 했다. UI에서 confidence 수치를 노출하지 않는지, 필드 자체를 둘지/뺄지 구현 시 점검한다. (현재 `src/client/app.js`는 confidence bar와 "근거 선명" 같은 문구를 노출 중이다.)
  - `TripFact.value`를 `missing`/`conflict` 표현을 위해 `string | null`로 확장할지 구현 전 판단한다.
  - 결정 축을 서버/eval이 읽어야 하면 `ReviewDecision`(또는 카드 출처 필드)을 공유 타입으로 승격한다. 현재 공유 타입에 미존재 — `src/client/` local state로 둔다.
  - 대시보드 카테고리 축을 계약으로 올리려면 `TripFact.category` 추가를 판단한다.
