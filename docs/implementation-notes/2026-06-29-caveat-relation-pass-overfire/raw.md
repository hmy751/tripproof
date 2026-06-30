# Raw Notes - caveat relation pass 과잉강등 (eval 출처와 측정값)

이 파일은 `index.md` 관찰의 배경 재료다. run artifact가 `.gitignore` 대상이라 핵심 수치를 여기 발췌·보존한다. 현재 실행 기준이나 작업 대기열이 아니다.

## 출처 (provenance)

모두 같은 입력으로 production eval을 돌렸다.
- material: `fixtures/private/accommodation-checkin/agoda-fukuoka-booking-confirmation-private.pdf`
- questions: `eval/datasets/agoda-booking-confirmation/questions.json` (8문항)
- runtime: `production` / retrieval `supabase`(top_k=3) / embedding `nomic-embed-text-v2-moe` / answer `gemma3:4b` / seed `20260624` / temperature `0.0`
- run 경로 base: `eval/runs/question-dataset/2026-06-19-agoda-original-pdf-qa-improvement/` (전부 gitignore — 아래 run-id 폴더로 재접근)

| run | 무엇 | 코드 | run-id 폴더 |
| --- | --- | --- | --- |
| 16 | 답과 함께 caveat 묻기(inline) | commit `5d1880f` | `16-evidence-relation-layer-06-after-production/` |
| 17 | caveat 따로 묻기(분리 호출, 문서째 "조건 있냐") | commit `574dee4` | `17-evidence-relation-pass-separated/` |
| 18 | per-unit(B) — unit마다 "이 답 제한하나" | commit `118a916`, `TRIPPROOF_CAVEAT_EXTRACTOR_MODE=pairwise` | `18-caveat-pairwise-B/` |
| 19 | 순서 불변(A) — B를 순서 뒤집어 2회 교집합 | commit `118a916`, `TRIPPROOF_CAVEAT_EXTRACTOR_MODE=order_invariant` | `19-caveat-order-invariant-A/` |

`118a916`은 `8040665`로 되돌렸다. answer composer 출력엔 run 간 비결정성이 있어 evidence_state 자체는 흔들린다(03 관찰). 아래 *과잉 부착* 패턴은 그 변동과 무관하게 반복 관찰됐다.

## evidence_state: run 17 → 18(B) → 19(A)

| 질문 | 기대 | 17(분리·문서째) | 18(B per-unit) | 19(A 순서불변) |
| --- | --- | --- | --- | --- |
| P0-01 체크인 준비물 | supported | supported | needs_review | needs_review |
| P0-02 체크인/체크아웃 날짜 | supported | needs_review | needs_review | needs_review |
| P0-03 체크인 시작 시각 | missing | missing | missing | missing |
| P0-04 숙소 이름·위치 | supported | missing | supported | needs_review×2 |
| P0-05 객실·인원 | supported | needs_review | needs_review | supported |
| P0-06 취소·노쇼 | supported | missing | supported | missing |
| P0-07 현장 추가비용 | supported | needs_review | missing | missing |
| P1-01 특별요청 확정? | needs_review | needs_review(노쇼,오답) | needs_review(정답 caveat) | needs_review(노쇼 drift, 3 items) |

(run 16: supported가 P1-01 포함 대부분, 유일하게 P0-07만 caveat로 강등 — 즉 inline 방식은 거의 안 발동.)

## 과잉으로 부착된 caveat 발췌 (limited_by_caveat 강등)

무관한 조건이 깨끗한 답에 붙은 자리. 이게 과잉강등의 실체다.

```
P0-01 체크인 준비물(기대 supported) ← "체크인 시 ... 유효한 신분증을 반드시 제시해야 합니다" (신분증 정책)   [18·19]
P0-02 날짜(기대 supported)         ← "2025년 3월 8일 전에 예약 취소 시 예약 무료 취소 가능!" (취소 정책)        [17·18·19]
P0-05 객실/인원(기대 supported)    ← "체크인 시 예약의 대표 투숙객 성함과 동일함을 확인하는 ..." (신분증 정책)  [17·18]
P0-04 위치(기대 supported)         ← "모든 객실은 체크인 당일에만 보장됩니다 ." (객실 보장 정책)               [19, A에서 새로]
P1-01 특별요청(기대 needs_review)  ← 18: "체크인 시 숙소 측의 상황에 따라 반영 여부가 결정됩니다 ." (정답)
                                   ← 17·19: "노쇼(No-Show) ... 100% ..." (오답, 특별요청과 무관)
```

관찰 포인트:
- P0-02 취소정책 부착은 17·18·19 *세 run 모두* 나왔다 — 일관된 오판(noise 아님)이라 순서 불변(A)으로도 안 걸렸다.
- per-unit(B)만 P1-01에 *정답 caveat*을 붙였다. A는 순서 뒤집기 과정에서 P1-01 답이 노쇼로 분해돼(3 items) 정답을 놓쳤다.
- A는 P0-05 과잉은 걸렀지만 P0-04에 새 과잉을 들였다 — 단일 run 변동 범위 안이라 A가 B보다 낫다고 못 한다.

## 재진입 메모

- per-unit·순서 불변(`118a916`)은 측정으로 효과를 못 봐 되돌렸다(`8040665`). 분리 호출 baseline(`574dee4`)은 유지.
- 같은 비교를 다시 하려면 위 출처 블록(seed/PDF/questions)으로 production run을 재현하고, `TRIPPROOF_CAVEAT_EXTRACTOR_MODE`는 `118a916`을 체크아웃해야 동작한다(현재 HEAD엔 없음).
- 다음 도전은 per-unit(B)에서 출발 + 검출만 더 강한 모델 / 또는 repeat run으로 noise 제거 후 측정.
