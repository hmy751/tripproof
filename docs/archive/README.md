# docs/archive

동결 스냅샷·참조 보관소다. 여기 있는 파일은 **활성 문서가 아니다.**

- **갱신하지 않는다.** 과거 어느 시점의 상태를 그대로 보존한다.
- 현재 제품 기준은 `docs/product-model.md`(통합 모델 기준 문서)와 `docs/prd.md`다.
- 다른 문서가 여기를 참조할 때는 **출처·출발점·UX 원천**으로만 가리킨다. 이 폴더가 최신이어야 한다고 가정하지 않는다 (의존은 일방향: 활성 문서 → archive 인용 OK / archive → 활성 문서 동기화 의무 없음).
- 새 UX·문서 탐색이 필요하면 이 스냅샷을 고치지 말고 **새 문서/prototype을 따로 만든다.**

## 보관 항목

- `preview/` — chat-first preview. TripProof 제품 문서 통합(2026-05-30)의 출발점이자 UX 감각 원천.
  - `prd.md` — chat-first UX PRD. 내용은 `docs/product-model.md`·`docs/prd.md`로 승격됨. (상단에 supersede 배너 있음)
  - `tripproof-preview-c.html` — C안 통합 프리뷰 목업 (확인/대시보드/현장 탭, 오른쪽 rail 후보, 인라인 근거).
  - `tripproof-preview-ux.html` — UX 프리뷰 목업.
- `spec-driven/` — 과거 spec-driven 구조 문서 스냅샷. 현재 specs 운영 기준은 `docs/specs/README.md`이고, light loop 결정 배경은 `docs/decisions/2026-06-03-light-spec-driven-loop/`다.
  - `00-spec-driven-development.md` — 초기 spec 운영 원칙과 문서 후보를 담은 archive 문서. 현재 queue나 gate가 아니다.
