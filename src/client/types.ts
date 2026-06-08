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
  tone?: "neutral" | "blocked";
};

export type QuestionResponse = {
  status: "accepted" | "blocked";
  message: string;
  materialIds: string[];
  materialCount: number;
  pageCount: number;
  charCount: number;
  excerpt?: string | null;
};
