export type LibraryItem = {
  id: string;
  name: string;
  fileName: string;
  status: "queued" | "reading" | "ready" | "failed";
};

export type View = "ask" | "board" | "field";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  tone?: "neutral" | "blocked";
};
