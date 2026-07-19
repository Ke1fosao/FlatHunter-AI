import { existsSync } from "node:fs";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type ApiRequestOptions = {
  method?: string;
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

type ApiClientModule = {
  apiRequest: <T>(endpoint: string, options?: ApiRequestOptions) => Promise<T>;
  setCsrfToken: (token: string) => void;
};

const modulePath = join(process.cwd(), "src/lib/api-client.ts");
const clientImportPath = "@/lib/api-client";

async function loadClient(): Promise<ApiClientModule> {
  const imported: unknown = await import(clientImportPath);
  return imported as ApiClientModule;
}

describe("same-origin API client", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("always calls the same-origin /api/v1 gateway", async () => {
    expect(existsSync(modulePath), "api-client.ts must exist").toBe(true);
    const { apiRequest } = await loadClient();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ready" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/health/");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/health/",
      expect.objectContaining({
        credentials: "include",
        cache: "no-store",
      }),
    );
  });

  it("adds the Telegram-auth CSRF token to unsafe requests", async () => {
    expect(existsSync(modulePath), "api-client.ts must exist").toBe(true);
    const { apiRequest, setCsrfToken } = await loadClient();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "profile-1" }), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    setCsrfToken("telegram-csrf-token");
    await apiRequest("/search-profiles/", {
      method: "POST",
      body: { name: "Львів" },
    });

    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(request.headers);
    expect(headers.get("X-CSRFToken")).toBe("telegram-csrf-token");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(request.body).toBe(JSON.stringify({ name: "Львів" }));
  });

  it("restores the CSRF token from sessionStorage after navigation", async () => {
    expect(existsSync(modulePath), "api-client.ts must exist").toBe(true);
    window.sessionStorage.setItem("flathunter-csrf", "stored-token");
    vi.resetModules();
    const { apiRequest } = await loadClient();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/listings/id/favorite/", {
      method: "POST",
      body: { value: true },
    });

    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(request.headers).get("X-CSRFToken")).toBe("stored-token");
  });

  it("returns normalized API errors", async () => {
    expect(existsSync(modulePath), "api-client.ts must exist").toBe(true);
    const { apiRequest } = await loadClient();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: { code: "not_authenticated", message: "Authentication required" },
          }),
          {
            status: 401,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    await expect(apiRequest("/me/")).rejects.toEqual(
      expect.objectContaining({
        name: "ApiClientError",
        status: 401,
        code: "not_authenticated",
        message: "Authentication required",
      }),
    );
  });
});
