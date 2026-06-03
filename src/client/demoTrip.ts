import type { TripProofResult } from "../shared/tripFacts";

export type CardSource = "ai_supported" | "manual";

export type CardDecision = {
  factId: string;
  state: "draft" | "confirmed" | "dismissed";
  source?: CardSource;
  fieldSaved?: boolean;
  valueOverride?: string;
};

export const demoTrip: TripProofResult = {
  artifacts: [
    {
      id: "hotel-booking",
      name: "호텔 예약 확인서",
      fileName: "hotel-booking-confirmation.png",
      kind: "image",
    },
    {
      id: "host-message",
      name: "호스트 체크인 안내",
      fileName: "host-checkin-message.txt",
      kind: "message",
    },
  ],
  facts: [
    {
      id: "checkin-start",
      schedule: "숙소 체크인",
      label: "체크인 시작 시간",
      value: "15:00",
      confidence: 0.96,
      evidenceState: "supported",
      evidence: [
        {
          artifactId: "hotel-booking",
          label: "호텔 예약 확인서",
          locator: "예약 요약 영역",
          snippet: "체크인 15:00. 체크아웃 11:00.",
        },
      ],
    },
    {
      id: "late-arrival",
      schedule: "숙소 체크인",
      label: "늦은 도착 조건",
      value: "22:00 이후 도착 시 호스트에게 연락",
      confidence: 0.72,
      evidenceState: "needs_review",
      evidence: [
        {
          artifactId: "host-message",
          label: "호스트 체크인 안내",
          locator: "도착 지연 안내",
          snippet: "22:00 이후 도착하면 메시지로 알려주세요. 출입 코드는 도착 당일 전달합니다.",
        },
      ],
    },
    {
      id: "door-code",
      schedule: "숙소 체크인",
      label: "출입 코드",
      value: null,
      confidence: 0.48,
      evidenceState: "needs_review",
      sensitive: true,
      evidence: [
        {
          artifactId: "host-message",
          label: "호스트 체크인 안내",
          locator: "셀프 체크인 안내",
          snippet: "출입 코드는 도착 당일 전달합니다.",
        },
      ],
    },
  ],
  openIssues: [
    {
      id: "late-arrival-review",
      label: "늦은 도착 조건",
      reason: "근거는 있으나 실제 연락 방식과 출입 코드 전달 시점은 직접 확인이 필요하다.",
      evidenceState: "needs_review",
    },
    {
      id: "door-code-review",
      label: "출입 코드",
      reason: "민감 정보라 자동 저장하지 않고 현장에서 직접 확인하도록 남긴다.",
      evidenceState: "needs_review",
    },
  ],
};

export const suggestedQuestions = [
  {
    factId: "checkin-start",
    text: "체크인은 몇 시부터야?",
  },
  {
    factId: "late-arrival",
    text: "늦게 도착하면 어떻게 해야 해?",
  },
  {
    factId: "door-code",
    text: "출입 코드는 어디 있어?",
  },
];
