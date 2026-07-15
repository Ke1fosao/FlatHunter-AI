export type HealthResponse = {
  status: "ready" | "degraded";
  service: string;
  checks: Record<string, "ok" | "error">;
};

export type AuthenticatedUser = {
  id: string;
  telegramId: number;
  firstName: string;
  lastName: string;
  username: string;
  locale: string;
  role: string;
};

type TelegramAuthResponse = {
  user: AuthenticatedUser;
  csrfToken: string;
};

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = "api_error"
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function normalizeApiBaseUrl(value: string | undefined): string {
  const candidate = value?.trim();
  if (!candidate) {
    return "/api/v1";
  }
  const normalized = candidate.replace(/\/+$/, "");
  return normalized.length > 0 ? normalized : "/api/v1";
}

export function buildApiUrl(baseUrl: string | undefined, endpoint: string): string {
  const base = normalizeApiBaseUrl(baseUrl);
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${base}${path}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & ApiErrorPayload;
  if (!response.ok) {
    throw new ApiError(
      payload.error?.message ?? `API request failed with status ${String(response.status)}`,
      response.status,
      payload.error?.code
    );
  }
  return payload;
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;

export async function fetchBackendHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(buildApiUrl(apiBaseUrl, "/health/"), {
    credentials: "include",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal
  });
  return parseResponse<HealthResponse>(response);
}

export async function authenticateTelegram(
  initData: string,
  signal?: AbortSignal
): Promise<TelegramAuthResponse> {
  const response = await fetch(buildApiUrl(apiBaseUrl, "/auth/telegram/"), {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ initData }),
    signal
  });
  return parseResponse<TelegramAuthResponse>(response);
}
