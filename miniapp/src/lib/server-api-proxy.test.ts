import { existsSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it, vi } from "vitest";

const modulePath = join(process.cwd(), "src/lib/server-api-proxy.ts");
const proxyImportPath = "@/lib/server-api-proxy";

describe("server API proxy", () => {
  it("forwards method, query, body, cookies and CSRF to the fixed backend", async () => {
    expect(existsSync(modulePath), "server-api-proxy.ts must exist").toBe(true);
    const { proxyApiRequest } = await import(proxyImportPath);
    const backendHeaders = new Headers({ "Content-Type": "application/json" });
    backendHeaders.append(
      "Set-Cookie",
      "flathunter_session=session-value; Path=/; HttpOnly; Secure; SameSite=Lax",
    );
    backendHeaders.append(
      "Set-Cookie",
      "csrftoken=csrf-value; Path=/; Secure; SameSite=Lax",
    );
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: backendHeaders,
      }),
    );
    const request = new Request(
      "https://miniapp.example.com/api/v1/listings/listing-1/favorite/?force=true",
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Cookie: "flathunter_session=session-value; csrftoken=csrf-value",
          Origin: "https://miniapp.example.com",
          "X-CSRFToken": "csrf-value",
          "Idempotency-Key": "request-1",
        },
        body: JSON.stringify({ value: true }),
      },
    );

    const response = await proxyApiRequest(
      request,
      ["listings", "listing-1", "favorite"],
      {
        backendApiUrl: "https://backend.example.com/api/v1",
        fetchImpl: fetchMock,
      },
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [target, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(target).toBe(
      "https://backend.example.com/api/v1/listings/listing-1/favorite/?force=true",
    );
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ value: true }));
    const headers = new Headers(init.headers);
    expect(headers.get("Cookie")).toContain("flathunter_session=session-value");
    expect(headers.get("X-CSRFToken")).toBe("csrf-value");
    expect(headers.get("Idempotency-Key")).toBe("request-1");
    expect(headers.get("Origin")).toBe("https://backend.example.com");
    expect(response.status).toBe(200);
    expect(response.headers.get("Set-Cookie")).toContain(
      "flathunter_session=session-value",
    );
    expect(response.headers.get("Set-Cookie")).toContain("csrftoken=csrf-value");
  });

  it("does not forward arbitrary incoming hosts as a backend destination", async () => {
    expect(existsSync(modulePath), "server-api-proxy.ts must exist").toBe(true);
    const { proxyApiRequest } = await import(proxyImportPath);
    const fetchMock = vi.fn();
    const request = new Request(
      "https://attacker.example/api/v1/health/?target=https://evil.example",
    );

    const response = await proxyApiRequest(request, ["health"], {
      backendApiUrl: "https://backend.example.com/api/v1",
      fetchImpl: fetchMock,
    });

    const [target] = fetchMock.mock.calls[0] as [string];
    expect(target).toBe(
      "https://backend.example.com/api/v1/health/?target=https%3A%2F%2Fevil.example",
    );
    expect(response.status).toBe(200);
  });

  it("rejects path traversal before contacting the backend", async () => {
    expect(existsSync(modulePath), "server-api-proxy.ts must exist").toBe(true);
    const { proxyApiRequest } = await import(proxyImportPath);
    const fetchMock = vi.fn();
    const request = new Request("https://miniapp.example.com/api/v1/admin/");

    const response = await proxyApiRequest(request, ["..", "admin"], {
      backendApiUrl: "https://backend.example.com/api/v1",
      fetchImpl: fetchMock,
    });

    expect(fetchMock).not.toHaveBeenCalled();
    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "invalid_proxy_path",
        message: "The requested API path is invalid.",
      },
    });
  });

  it("returns a normalized error for an invalid backend configuration", async () => {
    expect(existsSync(modulePath), "server-api-proxy.ts must exist").toBe(true);
    const { proxyApiRequest } = await import(proxyImportPath);
    const request = new Request("https://miniapp.example.com/api/v1/health/");

    const response = await proxyApiRequest(request, ["health"], {
      backendApiUrl: "file:///etc/passwd",
      fetchImpl: vi.fn(),
    });

    expect(response.status).toBe(500);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "invalid_backend_config",
        message: "The backend API URL is not configured safely.",
      },
    });
  });

  it("returns 502 when the backend cannot be reached", async () => {
    expect(existsSync(modulePath), "server-api-proxy.ts must exist").toBe(true);
    const { proxyApiRequest } = await import(proxyImportPath);
    const request = new Request("https://miniapp.example.com/api/v1/health/");

    const response = await proxyApiRequest(request, ["health"], {
      backendApiUrl: "https://backend.example.com/api/v1",
      fetchImpl: vi.fn().mockRejectedValue(new TypeError("fetch failed")),
    });

    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toEqual({
      error: {
        code: "backend_unavailable",
        message: "FlatHunter backend is temporarily unavailable.",
      },
    });
  });
});
