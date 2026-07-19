import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();
const source = (path: string): string =>
  readFileSync(join(root, path), "utf8");

describe("production API contract", () => {
  it("keeps browser traffic on the same-origin gateway", () => {
    const client = source("src/lib/api-client.ts");
    expect(client).toContain('const CLIENT_API_BASE = "/api/v1"');
    expect(client).toContain('headers.set("X-CSRFToken", token)');
    expect(client).toContain('credentials: "include"');
    expect(client).not.toContain("NEXT_PUBLIC_API_URL");
  });

  it("proxies every supported method to the server-only backend URL", () => {
    const route = source("src/app/api/v1/[...path]/route.ts");
    const proxy = source("src/lib/server-api-proxy.ts");
    ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"].forEach(
      (method) => {
        expect(route).toContain(`export function ${method}`);
      },
    );
    expect(proxy).toContain("process.env.BACKEND_API_URL");
    expect(proxy).toContain("backend_unavailable");
    expect(proxy).toContain("invalid_proxy_path");
    expect(proxy).toContain('headers.append("Set-Cookie"');
  });

  it("stores Telegram CSRF before protected route requests", () => {
    const api = source("src/lib/api.ts");
    const context = source("src/components/miniapp-context.tsx");
    expect(api).toContain("setCsrfToken(payload.csrfToken)");
    expect(api).not.toContain(
      "window.dispatchEvent(new Event(TELEGRAM_AUTHENTICATED_EVENT))",
    );
    expect(context).toContain('authStatus === "authenticated"');
    expect(context).toContain(
      "window.dispatchEvent(new Event(TELEGRAM_AUTHENTICATED_EVENT))",
    );
  });
});
