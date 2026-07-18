import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const layoutSource = readFileSync(new URL("./layout.tsx", import.meta.url), "utf8");

describe("root layout styles", () => {
  it("loads the dedicated search wizard stylesheet globally", () => {
    expect(layoutSource).toContain('import "./search-wizard.css";');
  });
});
