import type { ComponentType } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const profile = {
  id: "profile-1",
  name: "Львів",
  city: "Львів",
  is_active: true,
};

const listing = {
  id: "listing-1",
  source_name: "OLX",
  source_url: "https://example.com/olx",
  canonical_url: "https://example.com/olx",
  title: "Квартира біля центру",
  description: "Опис",
  deal_type: "rent",
  property_type: "apartment",
  city: "Львів",
  district: "Франківський",
  street: "Наукова",
  price_uah: 17500,
  currency: "UAH",
  rooms: 1,
  total_area: "42.00",
  floor: 4,
  floors_total: 9,
  building_type: "new_build",
  renovation_level: "good",
  heating_type: "autonomous",
  pets_allowed: true,
  children_allowed: true,
  commission_percent: "0.00",
  is_owner: true,
  images: [],
  attributes: {},
  published_at: "2026-07-19T00:00:00Z",
  is_demo: false,
  user_state: {
    is_favorite: false,
    is_hidden: false,
    is_compared: false,
    note: "",
    updated_at: null,
  },
  cluster_id: "cluster-1",
  source_count: 3,
  member_count: 3,
  is_cluster_primary: true,
  price_min_uah: 16500,
  price_max_uah: 18000,
};

const mocks = vi.hoisted(() => ({
  fetchSearchProfiles: vi.fn(),
  fetchClusterFeed: vi.fn(),
  setClusterState: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {},
  fetchSearchProfiles: mocks.fetchSearchProfiles,
}));

vi.mock("@/lib/cluster-api", () => ({
  fetchClusterFeed: mocks.fetchClusterFeed,
  setClusterState: mocks.setClusterState,
  sourceLabel: (count: number) => `${String(count)} джерела`,
  formatClusterPriceRange: (minimum: number, maximum: number) =>
    `${String(minimum)}–${String(maximum)} грн`,
}));

type WorkspaceModule = {
  SearchResultsWorkspace: ComponentType;
};

async function loadWorkspace(): Promise<WorkspaceModule> {
  const imported: unknown = await import("@/components/search-results-workspace");
  return imported as WorkspaceModule;
}

describe("SearchResultsWorkspace", () => {
  beforeEach(() => {
    mocks.fetchSearchProfiles.mockReset().mockResolvedValue([profile]);
    mocks.fetchClusterFeed.mockReset().mockResolvedValue([
      {
        listing,
        match: {
          score: 86,
          eligible: true,
          summary: "Добре відповідає умовам",
          strengths: [],
          compromises: [],
          unknowns: [],
          components: [],
        },
      },
    ]);
    mocks.setClusterState.mockReset().mockResolvedValue({
      id: "cluster-1",
      primary: {
        ...listing,
        user_state: { ...listing.user_state, is_favorite: true },
      },
      user_state: { ...listing.user_state, is_favorite: true },
    });
  });

  it("renders one routed card with cluster sources and price range", async () => {
    const { SearchResultsWorkspace } = await loadWorkspace();
    render(<SearchResultsWorkspace />);

    expect(await screen.findByText("Квартира біля центру")).toBeInTheDocument();
    expect(screen.getByText("3 джерела")).toBeInTheDocument();
    expect(screen.getByText("16500–18000 грн")).toBeInTheDocument();
    expect(screen.getByText("86% Match")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Відкрити Квартира біля центру" }),
    ).toHaveAttribute(
      "href",
      "/listings/listing-1?profile=profile-1&cluster=cluster-1",
    );
  });

  it("applies city, district, room, price and text filters", async () => {
    const { SearchResultsWorkspace } = await loadWorkspace();
    render(<SearchResultsWorkspace />);
    await screen.findByText("Квартира біля центру");

    fireEvent.change(screen.getByLabelText("Район"), {
      target: { value: "Сихівський" },
    });
    expect(screen.queryByText("Квартира біля центру")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Район"), {
      target: { value: "Франківський" },
    });
    fireEvent.change(screen.getByLabelText("Текст"), {
      target: { value: "Наукова" },
    });
    expect(screen.getByText("Квартира біля центру")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Максимальна ціна"), {
      target: { value: "16000" },
    });
    expect(screen.queryByText("Квартира біля центру")).not.toBeInTheDocument();
  });

  it("persists favorite state at cluster level", async () => {
    const { SearchResultsWorkspace } = await loadWorkspace();
    render(<SearchResultsWorkspace />);

    fireEvent.click(await screen.findByRole("button", { name: "В обране" }));

    await waitFor(() => {
      expect(mocks.setClusterState).toHaveBeenCalledWith("cluster-1", {
        is_favorite: true,
      });
    });
    expect(screen.getByRole("button", { name: "В обраному" })).toBeInTheDocument();
  });
});
