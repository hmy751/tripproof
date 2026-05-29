# Providers

OpenAI, local mock, OCR 같은 외부 호출 adapter를 여기에 둔다.

provider는 모델 호출과 응답 원형을 다루고, 사용자에게 보여줄 product 상태 판단은 `normalizeTripFacts.ts`로 넘긴다.
