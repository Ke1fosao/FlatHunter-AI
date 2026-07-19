const CLIENT_API_BASE = "/api/v1";
const CSRF_STORAGE_KEY = "flathunter-csrf";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
};

export type ApiRequestOptions = Omit<RequestInit, "body" | "method"> & {
  method?: string;
  body?: unknown;
};

export class ApiClientError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;

  constructor(
    message: string,
    status: number,
    code?: string,
    details?: unknown,
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let inMemoryCsrfToken = "";

function storedCsrfToken(): string {
  if (inMemoryCsrfToken) {
    return inMemoryCsrfToken;
  }
  if (typeof window === "undefined") {
    return "";
  }
  inMemoryCsrfToken = window.sessionStorage.getItem(CSRF_STORAGE_KEY) ?? "";
  return inMemoryCsrfToken;
}

export function setCsrfToken(token: string): void {
  inMemoryCsrfToken = token.trim();
  if (typeof window === "undefined") {
    return;
  }
  if (inMemoryCsrfToken) {
    window.sessionStorage.setItem(CSRF_STORAGE_KEY, inMemoryCsrfToken);
  } else {
    window.sessionStorage.removeItem(CSRF_STORAGE_KEY);
  }
}

export function clearCsrfToken(): void {
  setCsrfToken("");
}

export function buildClientApiUrl(endpoint: string): string {
  const trimmed = endpoint.trim();
  const withoutLeadingSlashes = trimmed.replace(/^\/+/, "");
  return `${CLIENT_API_BASE}/${withoutLeadingSlashes}`;
}

function isNativeBody(value: unknown): value is BodyInit {
  return (
    typeof value === "string" ||
    value instanceof Blob ||
    value instanceof FormData ||
    value instanceof URLSearchParams ||
    value instanceof ArrayBuffer ||
    ArrayBuffer.isView(value)
  );
}

async function responsePayload(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json().catch(() => ({}));
  }
  return response.text().catch(() => "");
}

export async function apiRequest<T>(
  endpoint: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  let requestBody: BodyInit | undefined;
  if (options.body !== undefined) {
    if (isNativeBody(options.body)) {
      requestBody = options.body;
    } else {
      requestBody = JSON.stringify(options.body);
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
    }
  }

  if (UNSAFE_METHODS.has(method)) {
    const token = storedCsrfToken();
    if (token && !headers.has("X-CSRFToken")) {
      headers.set("X-CSRFToken", token);
    }
  }

  const response = await fetch(buildClientApiUrl(endpoint), {
    ...options,
    method,
    body: requestBody,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  const payload = await responsePayload(response);

  if (!response.ok) {
    const errorPayload =
      payload !== null && typeof payload === "object"
        ? (payload as ApiErrorPayload)
        : {};
    throw new ApiClientError(
      errorPayload.error?.message ??
        `API request failed with status ${String(response.status)}`,
      response.status,
      errorPayload.error?.code,
      errorPayload.error?.details,
    );
  }

  return payload as T;
}
