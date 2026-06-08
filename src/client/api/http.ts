export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
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
