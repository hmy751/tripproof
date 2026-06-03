import type { TripProofResult } from "../shared/tripFacts";

export type Category = "숙소" | "투어" | "렌터카" | "결제";
export type PhaseKey = "pre" | "day1" | "day2" | "day4" | "common";

export type CardSource = "ai_supported" | "manual";

export type CardDecision = {
  factId: string;
  state: "confirmed" | "dismissed";
  source: CardSource;
  fieldSaved?: boolean;
  titleOverride?: string;
  valueOverride?: string;
  category: Category;
  phase: PhaseKey;
};

export type CandidateMeta = {
  factId: string;
  category: Category;
  phase: PhaseKey;
  question: string;
  note: string;
};

export const phases: Array<{ key: PhaseKey; label: string; when: string }> = [
  { key: "pre", label: "출발 전", when: "D-3" },
  { key: "day1", label: "Day 1", when: "도착·체크인" },
  { key: "day2", label: "Day 2", when: "후지산 투어" },
  { key: "day4", label: "Day 4", when: "렌터카 반납" },
  { key: "common", label: "공통", when: "결제·기타" },
];

export const categoryColors: Record<Category, string> = {
  숙소: "#2f6bf0",
  투어: "#1f7a3d",
  렌터카: "#966200",
  결제: "#6c3fb4",
};

export const artifactNotes: Record<string, string> = {
  "hotel-booking": "체크인·늦은 도착·예약번호",
  "host-message": "출입 코드·도착 지연 연락",
  "fuji-voucher": "모바일 바우처·집합 시간",
  "rental-terms": "연료 정책·보증금",
  "city-tax": "도시세·추가 결제 이유",
};

export const demoTrip: TripProofResult = {
  artifacts: [
    {
      id: "hotel-booking",
      name: "호텔 예약 화면",
      fileName: "hotel-booking.png",
      kind: "image",
    },
    {
      id: "host-message",
      name: "호스트 체크인 안내",
      fileName: "host-message.png",
      kind: "image",
    },
    {
      id: "fuji-voucher",
      name: "후지산 투어 바우처",
      fileName: "fuji-voucher.pdf",
      kind: "pdf",
    },
    {
      id: "rental-terms",
      name: "렌터카 예약 약관",
      fileName: "rental-terms.pdf",
      kind: "pdf",
    },
    {
      id: "city-tax",
      name: "호텔 도시세 영수증",
      fileName: "city-tax.jpg",
      kind: "receipt",
    },
  ],
  facts: [
    {
      id: "late-arrival",
      schedule: "Day 1 · 도착·체크인",
      label: "늦은 도착",
      value: "22:00 이후 숙소 연락",
      confidence: 0.93,
      evidenceState: "supported",
      evidence: [
        {
          artifactId: "hotel-booking",
          label: "호텔 예약 화면",
          locator: "예약 요약 · 늦은 도착 안내",
          snippet: "체크인 22:00 이후 도착 시 숙소로 사전 연락 바랍니다.",
        },
        {
          artifactId: "host-message",
          label: "호스트 체크인 안내",
          locator: "호스트 메시지 · 셀프 체크인",
          snippet: "도착이 늦어지면 메시지를 남겨 주세요. 출입 안내를 다시 보내드립니다.",
        },
      ],
    },
    {
      id: "mobile-voucher",
      schedule: "Day 2 · 후지산 투어",
      label: "바우처 제시",
      value: "모바일 바우처 가능",
      confidence: 0.9,
      evidenceState: "supported",
      evidence: [
        {
          artifactId: "fuji-voucher",
          label: "후지산 투어 바우처",
          locator: "바우처 2쪽 · 제시 방법",
          snippet: "Mobile voucher accepted. Please show this screen at the meeting point.",
        },
      ],
    },
    {
      id: "fuel-policy",
      schedule: "Day 4 · 렌터카 반납",
      label: "연료 정책",
      value: "만탱크 반납 (full-to-full)",
      confidence: 0.88,
      evidenceState: "supported",
      evidence: [
        {
          artifactId: "rental-terms",
          label: "렌터카 예약 약관",
          locator: "약관 3조 · 연료",
          snippet: "Return the vehicle with a full tank. Refueling fee applies otherwise.",
        },
      ],
    },
    {
      id: "city-tax",
      schedule: "공통 · 결제·기타",
      label: "도시세",
      value: "JPY 1,200",
      confidence: 0.89,
      evidenceState: "supported",
      evidence: [
        {
          artifactId: "city-tax",
          label: "호텔 도시세 영수증",
          locator: "영수증 · 금액 영역",
          snippet: "City tax JPY 1,200",
        },
        {
          artifactId: "hotel-booking",
          label: "호텔 예약 화면",
          locator: "예약 요약 · 비고",
          snippet: "도시세는 현지에서 별도 결제됩니다.",
        },
      ],
    },
    {
      id: "door-code",
      schedule: "Day 1 · 도착·체크인",
      label: "출입 코드",
      value: null,
      confidence: 0.5,
      evidenceState: "needs_review",
      sensitive: true,
      evidence: [
        {
          artifactId: "host-message",
          label: "호스트 체크인 안내",
          locator: "호스트 메시지 · 출입 안내",
          snippet: "출입 코드는 도착 당일 다시 안내드립니다. (코드 본문은 가림)",
        },
      ],
    },
    {
      id: "late-tour-refund",
      schedule: "Day 2 · 후지산 투어",
      label: "지각 환불 규정",
      value: null,
      confidence: 0.15,
      evidenceState: "missing",
      evidence: [],
    },
    {
      id: "checkin-time",
      schedule: "Day 1 · 도착·체크인",
      label: "체크인 시간",
      value: "15:00",
      confidence: 0.96,
      evidenceState: "supported",
      evidence: [
        {
          artifactId: "hotel-booking",
          label: "호텔 예약 화면",
          locator: "예약 요약 · 체크인",
          snippet: "Check-in 15:00 / Check-out 11:00",
        },
      ],
    },
  ],
  openIssues: [
    {
      id: "door-code-review",
      label: "출입 코드",
      reason: "민감 정보라 자동 저장하지 않고 원문에서 직접 확인하도록 남긴다.",
      evidenceState: "needs_review",
    },
    {
      id: "late-tour-refund-missing",
      label: "지각 환불 규정",
      reason: "현재 자료에서는 환불 규정을 찾지 못했으므로 직접 확인이 필요하다.",
      evidenceState: "missing",
    },
  ],
};

export const candidateMeta: CandidateMeta[] = [
  {
    factId: "late-arrival",
    category: "숙소",
    phase: "day1",
    question: "호텔에 늦게 도착하면 어떻게 돼?",
    note: "두 자료가 같은 조건을 가리킵니다.",
  },
  {
    factId: "mobile-voucher",
    category: "투어",
    phase: "day2",
    question: "투어 바우처 프린트해야 해?",
    note: "프린트 불필요.",
  },
  {
    factId: "fuel-policy",
    category: "렌터카",
    phase: "day4",
    question: "렌터카 기름 채워서 반납해야 해?",
    note: "미충전 시 수수료.",
  },
  {
    factId: "city-tax",
    category: "결제",
    phase: "common",
    question: "이 영수증은 왜 낸 거야?",
    note: "체크인 시 별도 결제.",
  },
  {
    factId: "door-code",
    category: "숙소",
    phase: "day1",
    question: "출입 코드 뭐였지?",
    note: "민감 정보 — 원문에서 확인한 값만 입력하세요.",
  },
  {
    factId: "late-tour-refund",
    category: "투어",
    phase: "day2",
    question: "투어 늦으면 환불돼?",
    note: "AI 근거 미발견 — 직접 확인한 내용을 입력하세요.",
  },
];

export const extraQuestionMatches: Record<string, string> = {
  "체크인 몇 시부터야?": "checkin-time",
};

export const suggestedQuestions = candidateMeta.map((candidate) => ({
  factId: candidate.factId,
  text: candidate.question,
}));
