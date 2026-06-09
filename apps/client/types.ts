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
  excerpt?: string | null;
  facts?: FactCandidate[];
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

export type FactCandidate = {
  id: string;
  label: string;
  value?: string | null;
  evidenceState: EvidenceState;
  evidence: EvidenceRef[];
  sensitive: boolean;
  reason?: string | null;
};

export type QuestionResponse = {
  status: "accepted" | "blocked";
  message: string;
  materialIds: string[];
  materialCount: number;
  pageCount: number;
  charCount: number;
  excerpt?: string | null;
  excerptLocator?: string | null;
  excerptSourceUnitId?: string | null;
  facts?: FactCandidate[];
};
