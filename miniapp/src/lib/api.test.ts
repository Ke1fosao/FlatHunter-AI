import { describe, expect, it } from "vitest";

import { buildApiUrl, normalizeApiBaseUrl } from "@/lib/api";

describe("normalizeApiBaseUrl", () => {
  it("removes trailing slashes without changing a relative base", () => {
    expect(normalizeApiBaseUrl("/api/v1///")).toBe("/api/v1");
  });

  it("falls back to the gateway API path", () => {
    expect(normalizeApiBaseUrl(undefined)).toBe("/api/v1");
  });
});

describe("buildApiUrl", () => {
  it("joins the base URL and endpoint with one slash", () => {
    expect(buildApiUrl("https://api.example.com/api/v1/", "/health/")).toBe(
      "https://api.example.com/api/v1/health/"
    );
  });
});
