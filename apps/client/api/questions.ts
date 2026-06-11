import type { QuestionResponse } from "../types";
import { TRIPPROOF_CORRELATION_ID_HEADER, readJson } from "./http";

export async function askQuestion(
  question: string,
  materialIds: string[],
  correlationId?: string,
): Promise<QuestionResponse> {
  const response = await fetch("/api/questions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(correlationId ? { [TRIPPROOF_CORRELATION_ID_HEADER]: correlationId } : {}),
    },
    body: JSON.stringify({ question, materialIds }),
  });

  return readJson<QuestionResponse>(response);
}
