const DEFAULT_BACKEND_API_URL =
  "https://flathunter-ai-backend.onrender.com/api/v1";
const DEFAULT_TIMEOUT_MS = 30_000;
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "content-type",
  "cookie",
  "x-csrftoken",
  "idempotency-key",
  "x-request-id",
] as const;
const FORWARDED_RESPONSE_HEADERS = [
  "cache-control",
  "content-disposition",
  "content-language",
  "content-type",
  "etag",
  "last-modified",
  "location",
  "vary",
  "x-request-id",
] as const;

type ProxyDependencies = {
  backendApiUrl?: string;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
};

type HeadersWithSetCookie = Headers & {
  getSetCookie?: () => string[];
};

function errorResponse(
  status: number,
  code: string,
  message: string,
): Response {
  return Response.json({ error: { code, message } }, { status });
}

function nonEmpty(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : undefined;
}

function backendBaseUrl(configured?: string): URL | null {
  const publicApiUrl = nonEmpty(process.env.NEXT_PUBLIC_API_URL);
  const candidate =
    nonEmpty(configured) ??
    nonEmpty(process.env.BACKEND_API_URL) ??
    (publicApiUrl?.startsWith("http") === true ? publicApiUrl : undefined) ??
    DEFAULT_BACKEND_API_URL;
  try {
    const url = new URL(candidate);
    if (url.protocol !== "https:" && url.protocol !== "http:") {
      return null;
    }
    if (url.username || url.password) {
      return null;
    }
    url.hash = "";
    url.search = "";
    url.pathname = `${url.pathname.replace(/\/+$/, "")}/`;
    return url;
  } catch {
    return null;
  }
}

function safePath(path: string[]): string[] | null {
  const normalized: string[] = [];
  for (const rawSegment of path) {
    let decoded: string;
    try {
      decoded = decodeURIComponent(rawSegment);
    } catch {
      return null;
    }
    if (
      decoded.length === 0 ||
      decoded === "." ||
      decoded === ".." ||
      decoded.includes("/") ||
      decoded.includes("\\") ||
      decoded.includes("\0")
    ) {
      return null;
    }
    normalized.push(decoded);
  }
  return normalized;
}

function targetUrl(base: URL, request: Request, path: string[]): URL {
  const encodedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const target = new URL(`${encodedPath}/`, base);
  const source = new URL(request.url);
  source.searchParams.forEach((value, key) => {
    target.searchParams.append(key, value);
  });
  return target;
}

function requestHeaders(request: Request, backend: URL): Headers {
  const headers = new Headers();
  FORWARDED_REQUEST_HEADERS.forEach((name) => {
    const value = request.headers.get(name);
    if (value !== null) {
      headers.set(name, value);
    }
  });
  const method = request.method.toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("Origin", backend.origin);
    headers.set("Referer", `${backend.origin}/`);
  }
  return headers;
}

function rewrittenCookie(cookie: string): string {
  return cookie.replace(/;\s*Domain=[^;]+/gi, "");
}

function responseHeaders(source: Headers): Headers {
  const headers = new Headers();
  FORWARDED_RESPONSE_HEADERS.forEach((name) => {
    const value = source.get(name);
    if (value !== null) {
      headers.set(name, value);
    }
  });

  const extended = source as HeadersWithSetCookie;
  const cookies =
    typeof extended.getSetCookie === "function"
      ? extended.getSetCookie()
      : source.get("Set-Cookie")
        ? [source.get("Set-Cookie")!]
        : [];
  cookies.forEach((cookie) => {
    headers.append("Set-Cookie", rewrittenCookie(cookie));
  });
  return headers;
}

async function requestBody(request: Request): Promise<string | undefined> {
  if (["GET", "HEAD"].includes(request.method.toUpperCase())) {
    return undefined;
  }
  const body = await request.text();
  return body.length > 0 ? body : undefined;
}

export async function proxyApiRequest(
  request: Request,
  path: string[],
  dependencies: ProxyDependencies = {},
): Promise<Response> {
  const backend = backendBaseUrl(dependencies.backendApiUrl);
  if (!backend) {
    return errorResponse(
      500,
      "invalid_backend_config",
      "The backend API URL is not configured safely.",
    );
  }
  const normalizedPath = safePath(path);
  if (!normalizedPath) {
    return errorResponse(
      400,
      "invalid_proxy_path",
      "The requested API path is invalid.",
    );
  }

  const fetchImpl = dependencies.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => {
    controller.abort();
  }, dependencies.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  const abortProxy = () => {
    controller.abort();
  };
  request.signal.addEventListener("abort", abortProxy, { once: true });

  try {
    const response = await fetchImpl(
      targetUrl(backend, request, normalizedPath).toString(),
      {
        method: request.method,
        headers: requestHeaders(request, backend),
        body: await requestBody(request),
        redirect: "manual",
        cache: "no-store",
        signal: controller.signal,
      },
    );
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders(response.headers),
    });
  } catch {
    return errorResponse(
      502,
      "backend_unavailable",
      "FlatHunter backend is temporarily unavailable.",
    );
  } finally {
    globalThis.clearTimeout(timeout);
    request.signal.removeEventListener("abort", abortProxy);
  }
}
