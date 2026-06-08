import type { QuestionResponse } from "../types";
import { readJson } from "./http";

export async function askQuestion(question: string, materialIds: string[]): Promise<QuestionResponse> {
  const response = await fetch("/api/questions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, materialIds }),
  });

  return readJson<QuestionResponse>(response);
}
