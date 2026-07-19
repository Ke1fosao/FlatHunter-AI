import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

function source(path: string): string {
  return readFileSync(join(root, path), "utf8");
}

describe("Mini App routing contract", () => {
  it("redirects the root route to search", () => {
    expect(source("src/app/page.tsx")).toContain('redirect("/search")');
  });

  it("defines every user-facing route", () => {
    const routes = [
      "src/app/(miniapp)/search/page.tsx",
      "src/app/(miniapp)/map/page.tsx",
      "src/app/(miniapp)/favorites/page.tsx",
      "src/app/(miniapp)/compare/page.tsx",
      "src/app/(miniapp)/profile/page.tsx",
      "src/app/(miniapp)/listings/[id]/page.tsx",
    ];

    routes.forEach((route) => {
      expect(() => source(route)).not.toThrow();
    });
  });

  it("does not mount the old state-driven shell from the root page", () => {
    expect(source("src/app/page.tsx")).not.toContain("StageSixShell");
    expect(source("src/app/(miniapp)/layout.tsx")).toContain("MiniAppShell");
  });
});
