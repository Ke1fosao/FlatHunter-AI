import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const layoutSource = readFileSync(
  resolve(process.cwd(), "src/app/layout.tsx"),
  "utf8",
);

describe("root layout styles", () => {
  it("loads the dedicated search wizard stylesheet globally", () => {
    expect(layoutSource).toContain('import "./search-wizard.css";');
  });
});
