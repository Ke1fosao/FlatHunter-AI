import { describe, expect, it } from "vitest";

import { isMapFeatureCollection } from "@/lib/map-types";

const validCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      id: "listing-1",
      geometry: { type: "Point", coordinates: [24.0297, 49.8397] },
      properties: {
        id: "listing-1",
        title: "Квартира у Львові",
        price_uah: 18000,
        rooms: 2,
        total_area: "52.00",
        city: "Львів",
        district: "Галицький",
        street: "Зелена",
        is_demo: true,
        published_at: "2026-07-16T12:00:00Z",
        user_state: { is_favorite: false, is_hidden: false, is_compared: false },
        match: null
      }
    }
  ],
  meta: { returned: 1, inspected: 1, profile_id: null }
};

describe("isMapFeatureCollection", () => {
  it("accepts a valid point feature collection", () => {
    expect(isMapFeatureCollection(validCollection)).toBe(true);
  });

  it("rejects coordinates that are not a numeric longitude-latitude pair", () => {
    const invalid = structuredClone(validCollection);
    invalid.features[0].geometry.coordinates = [49.8397];

    expect(isMapFeatureCollection(invalid)).toBe(false);
  });

  it("rejects a feature without a listing title", () => {
    const invalid = structuredClone(validCollection) as unknown as {
      features: { properties: Record<string, unknown> }[];
    };
    delete invalid.features[0].properties.title;

    expect(isMapFeatureCollection(invalid)).toBe(false);
  });
});
