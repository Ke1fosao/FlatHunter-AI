import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const css = readFileSync(join(process.cwd(), "src/app/miniapp-shell.css"), "utf8");

describe("Mini App layering contract", () => {
  it("uses named layers for navigation and modals", () => {
    expect(css).toContain("--layer-navigation: 900");
    expect(css).toContain("--layer-modal: 1200");
    expect(css).toContain("z-index: var(--layer-navigation)");
    expect(css).toContain("z-index: var(--layer-modal) !important");
  });

  it("reserves bottom space and keeps the navigation pointer-safe", () => {
    expect(css).toContain("--bottom-nav-height");
    expect(css).toContain("padding: 0 16px calc(var(--bottom-nav-height)");
    expect(css).toContain("pointer-events: none");
    expect(css).toContain("pointer-events: auto");
  });
});
