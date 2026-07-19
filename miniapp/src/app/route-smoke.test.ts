import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const read = (path: string): string =>
  readFileSync(join(process.cwd(), path), "utf8");

describe("routed Mini App smoke contract", () => {
  it("renders exactly one primary navigation from the shared shell", () => {
    const shell = read("src/components/miniapp-shell.tsx");
    expect(shell.match(/<BottomNavigation/g)).toHaveLength(1);
    expect(shell).not.toContain("stage-six-switch");
    expect(shell).not.toContain("workspace-tabs");
  });

  it("uses dedicated listing detail links", () => {
    expect(read("src/components/listing-card.tsx")).toContain(
      "`/listings/${listing.id}`",
    );
    expect(read("src/components/map-workspace.tsx")).toContain(
      "`/listings/${listing.id}`",
    );
  });
});
