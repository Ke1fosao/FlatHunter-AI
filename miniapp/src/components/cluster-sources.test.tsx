import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ClusterSources } from "@/components/cluster-sources";
import type { ListingClusterDetail } from "@/lib/cluster-api";

const listing = {
  id: "listing-1", source_name: "Demo A", source_url: "https://example.invalid/a", canonical_url: "https://example.invalid/a", title: "Квартира", description: "", deal_type: "rent", property_type: "apartment", city: "Львів", district: "Центр", street: "Зелена", price_uah: 18000, price_min_uah: 18000, price_max_uah: 18500, currency: "UAH", rooms: 2, total_area: "50.00", floor: 3, floors_total: "9", building_type: "brick", renovation_level: "good", heating_type: "individual", pets_allowed: true, children_allowed: true, commission_percent: "0.00", is_owner: true, images: [], attributes: {}, published_at: "2026-07-16T12:00:00Z", is_demo: true, user_state: { is_favorite: false, is_hidden: false, is_compared: false, note: "", updated_at: null }, cluster_id: "cluster-1", source_count: 2, member_count: 2, is_cluster_primary: true
};

const cluster: ListingClusterDetail = {
  id: "cluster-1", status: "active", primary: listing, member_count: 2, source_count: 2, confidence_min: "94.00", confidence_max: "100.00", price_min_uah: 18000, price_max_uah: 18500,
  members: [
    { role: "primary", confidence: "100.00", joined_by: "exact", reasons: [], listing },
    { role: "duplicate", confidence: "94.00", joined_by: "auto", reasons: ["Однакова адреса"], listing: { ...listing, id: "listing-2", source_name: "Demo B", source_url: "https://example.invalid/b", price_uah: 18500, is_cluster_primary: false } }
  ],
  user_state: listing.user_state, match: null, algorithm_version: 1, created_at: "2026-07-16T12:00:00Z", updated_at: "2026-07-16T12:00:00Z"
};

describe("ClusterSources", () => {
  it("shows every source, price range and semantic links", () => {
    render(<ClusterSources cluster={cluster} />);
    expect(screen.getByText(/2 джерела/)).toBeInTheDocument();
    expect(screen.getByText("18 000–18 500 грн")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Відкрити це джерело/ })).toHaveLength(2);
    expect(screen.getByText("Основне")).toBeInTheDocument();
  });
});
