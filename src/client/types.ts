import type { Category, PhaseKey } from "./data/tripSession";

export type View = "ask" | "board" | "field";

export type ChatMessage =
  | { id: string; role: "ai"; kind: "intro" }
  | { id: string; role: "user"; text: string }
  | { id: string; role: "ai"; kind: "answer"; factId: string };

export type DraftCard = {
  factId: string;
  title: string;
  value: string;
  category: Category;
  phase: PhaseKey;
  originalTitle: string;
  originalValue: string;
};
