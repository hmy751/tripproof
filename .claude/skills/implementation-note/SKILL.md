---
name: implementation-note
description: TripProof에서 현재 대화/작업 세션에 docs/implementation-notes로 남길 구현 중 오해, drift, 경계 관찰이 있는지 판단하고, 충분하면 중립적인 구현 노트로 저장하며, 너무 약하면 저장하지 않는다고 말할 때 사용한다. "구현 노트로 남겨", "implementation note", "이번 대화에서 기록할 만한 오해가 있나", "docs/implementation-notes에 저장해줘" 같은 요청에 트리거한다.
---

# Implementation Note

이 skill은 TripProof repo에서 구현 중 발견한 오해, drift, 경계 관찰을 `docs/implementation-notes/`에 남길지 판단한다. 목적은 대화 원문 저장이 아니라, 이후 비슷한 구현에서 다시 볼 calibration sample을 남기는 것이다.

## 먼저 볼 것

- `docs/implementation-notes/README.md`
- `docs/engineering/README.md`
- 필요하면 관련 `docs/specs/**`, `docs/decisions/**`, `docs/work-log.md`, 최근 commit

## 저장할 만한 신호

- spec을 구현하다가 parent/인접 spec 계약을 잃은 사례.
- hard-coded value, fixture, stub, deterministic adapter가 product causality를 대신하려는 drift.
- LLM/RAG/evidence/state 같은 제품 경계를 구현 중 잘못 좁힌 사례.
- AI나 subagent가 반복해서 오해하기 쉬운 작업 경계.
- 다음 구현자가 같은 상황에서 다시 확인할 guardrail이 생겼다.

## 저장하지 않는 신호

- 단순 진행 상황, 완료 목록, 커밋 요약.
- 구조를 채택/기각/보류한 결정이라 `docs/decisions/`가 맞는 경우.
- 다음 세션 재진입만 돕는 얇은 작업 기록이라 `docs/work-log.md`가 맞는 경우.
- 제품 동작 기준이나 AC라 `docs/specs/`에 반영하는 게 맞는 경우.
- 대화 원문, 개인 로컬 맥락, 내부 도구 운영 로그만 있는 경우.
- 관찰이 아직 너무 약해 나중에 다시 봐도 구현 기준을 주지 못하는 경우.

## 작업 흐름

1. 현재 사용자 요청이 저장인지 판단만 원하는지 확인한다.
2. 현재 세션에서 관찰 후보를 1-3개로 압축한다.
3. `docs/implementation-notes/`가 맞는지 `decisions`, `work-log`, `specs`, commit 중 더 가까운 위치와 비교한다.
4. 너무 약하거나 다른 위치가 맞으면 파일을 만들지 말고 이유를 짧게 말한다.
5. 충분하면 README 기준대로 `docs/implementation-notes/YYYY-MM-DD-짧은-주제/`(폴더형 `index.md`, 배경 재료가 있으면 `raw.md`)를 만든다.
6. 필요한 경우에만 `docs/work-log.md`에 "구현 노트가 생겼다"는 링크를 아주 짧게 남긴다.

## 작성 기준

- 대화 원문을 붙이지 않는다.
- 독립적으로 읽히는 중립 표현으로 쓴다.
- "AI가 혼났다"가 아니라 "구현 중 어떤 경계가 흐려졌는지"를 쓴다.
- 현재 작업 queue나 승인 gate처럼 읽히지 않게 한다.
- 아직 없는 product proof, eval run, before/after를 완료된 것처럼 쓰지 않는다.

권장 파일 형식과 템플릿(`index.md`/`raw.md`)은 `docs/implementation-notes/README.md`를 따른다.
