export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export const TRIPPROOF_CORRELATION_ID_HEADER = "X-TripProof-Correlation-Id";

export function createCorrelationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `flow_${crypto.randomUUID()}`;
  }

  return `flow_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

export function correlationHeaders(correlationId: string | null | undefined): HeadersInit | undefined {
  if (!correlationId) {
    return undefined;
  }
  return {
    [TRIPPROOF_CORRELATION_ID_HEADER]: correlationId,
  };
}

export async function readJson<T>(response: Response): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T;
  }

  let message = "요청을 처리하지 못했습니다.";
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) {
      message = body.detail;
    }
  } catch {
    // Keep the default message when the backend returns a non-JSON error.
  }

  throw new ApiError(message);
}
