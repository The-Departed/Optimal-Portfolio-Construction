import type { ErrorCode, ErrorResponse } from "@/types/api";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");
/** Upper bound for any request (the slowest, a first 200,000-portfolio simulation, takes seconds). */
export const REQUEST_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: ErrorCode | "NETWORK_ERROR" | "TIMEOUT" | "UNKNOWN";
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: ApiError["code"],
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "code" in value &&
    "message" in value &&
    typeof (value as ErrorResponse).message === "string"
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError(0, "TIMEOUT", `The analytics API did not respond within ${REQUEST_TIMEOUT_MS / 1000} seconds.`);
    }
    throw new ApiError(0, "NETWORK_ERROR", "Unable to reach the analytics API. Is the backend running?");
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (isErrorResponse(body)) {
      throw new ApiError(response.status, body.code, body.message, body.details);
    }
    throw new ApiError(response.status, "UNKNOWN", `Request failed with status ${response.status}.`);
  }
  return body as T;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, payload: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(payload) }),
};
