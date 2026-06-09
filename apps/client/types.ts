export type LibraryItem = {
  id: string;
  name: string;
  fileName: string;
  contentType?: string | null;
  status: "ready" | "failed";
  pageCount?: number | null;
  preview?: string | null;
  error?: string | null;
};

export type View = "ask" | "board" | "field";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  meta?: string;
  answer?: ChatAnswer;
  tone?: "neutral" | "blocked";
};

export type EvidenceState = "supported" | "needs_review" | "missing" | "conflict";

export type EvidenceRef = {
  materialId: string;
  sourceUnitId: string;
  label: string;
  locator: string;
  snippet: string;
};

export type ChatAnswerItem = {
  id: string;
  label: string;
  body: string;
  evidenceState: EvidenceState;
  value?: string | null;
  evidence: EvidenceRef[];
};

export type ChatAnswer = {
  summary: string;
  items: ChatAnswerItem[];
};

export type QuestionResponse = {
  status: "accepted" | "blocked";
  message: string;
  answer: ChatAnswer;
  materialIds: string[];
  materialCount: number;
  pageCount: number;
  charCount: number;
};
