# Accommodation Check-In Extraction Prompt

체크인 fact proposer는 retrieval이 고른 source unit만 읽고 JSON object 하나를 반환한다.

## Grounding rule

- 제공된 source unit 밖의 일반 지식으로 값을 만들지 않는다.
- `supported`를 반환하려면 `source_unit_id`가 입력 후보 중 하나여야 한다.
- `supported`의 `evidence_snippet`은 해당 source unit text의 정확한 부분 문자열이어야 한다.
- 정확한 근거가 없으면 `missing`과 `value: null`을 반환한다.
- 체크인 날짜나 arrival 날짜는 체크인 시작 시각으로 해석하지 않는다.

## Output shape

```json
{
  "target_id": "string",
  "label": "string",
  "value": "string or null",
  "evidence_state": "supported | missing | needs_review",
  "source_unit_id": "string or null",
  "evidence_snippet": "string or null",
  "sensitive": false,
  "reason": "Korean sentence"
}
```
