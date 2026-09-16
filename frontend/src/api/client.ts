const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEV_USER_ID = import.meta.env.VITE_DEV_USER_ID || "";

export class ApiError extends Error {
  errorCode: string;
  detail: Record<string, unknown>;

  constructor(message: string, errorCode: string, detail: Record<string, unknown>) {
    super(message);
    this.errorCode = errorCode;
    this.detail = detail;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": DEV_USER_ID,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.message || response.statusText,
      body.error_code || "UNKNOWN_ERROR",
      body.detail || {}
    );
  }

  return response.json() as Promise<T>;
}