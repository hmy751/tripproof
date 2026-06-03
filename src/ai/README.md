# Python AI

`src/ai/`는 Python으로 작성하는 AI 후보 생성 코드를 둔다.

현재 경계는 좁게 유지한다.

- Python은 `RawTripFactCandidate` 모양의 후보 JSON을 만든다.
- prompt와 provider adapter는 AI 후보 생성 내부 구현이므로 이 폴더 아래에 둔다.
- TypeScript `src/server/trip-facts/normalizeTripFacts.ts`가 후보를 최종 `TripProofResult`로 정규화한다.
- `src/shared/tripFacts.ts`는 client와 TS server가 읽는 product contract다. Python은 TS 파일을 직접 import하지 않고, 같은 필드 이름을 가진 JSON 경계와 Python model을 참고한다.

로컬 확인:

```sh
PYTHONPATH=src/ai python3 -m tripproof_ai < src/ai/examples/accommodation_checkin.json
PYTHONPATH=src/ai python3 -m unittest discover -s src/ai/tests
```
