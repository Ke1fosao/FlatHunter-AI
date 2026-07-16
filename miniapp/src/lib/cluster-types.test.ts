import { describe, expect, it } from "vitest";

import { formatClusterPriceRange, sourceLabel } from "@/lib/cluster-api";

describe("cluster presentation helpers", () => {
  it("uses Ukrainian source pluralization", () => {
    expect(sourceLabel(1)).toBe("1 джерело");
    expect(sourceLabel(2)).toBe("2 джерела");
    expect(sourceLabel(5)).toBe("5 джерел");
    expect(sourceLabel(12)).toBe("12 джерел");
  });

  it("formats a stable price or range", () => {
    expect(formatClusterPriceRange(18000, 18000)).toBe("18 000 грн");
    expect(formatClusterPriceRange(18000, 18500)).toBe("18 000–18 500 грн");
  });
});
