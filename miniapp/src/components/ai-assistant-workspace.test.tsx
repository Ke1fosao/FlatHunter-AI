import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  compareListingsWithAI,
  fetchListings,
  fetchSearchProfiles,
  generateOwnerQuestionsWithAI,
  summarizeListingWithAI
} = vi.hoisted(() => ({
  compareListingsWithAI: vi.fn(),
  fetchListings: vi.fn(),
  fetchSearchProfiles: vi.fn(),
  generateOwnerQuestionsWithAI: vi.fn(),
  summarizeListingWithAI: vi.fn()
}));

vi.mock("@/lib/api", () => ({
  compareListingsWithAI,
  fetchListings,
  fetchSearchProfiles,
  generateOwnerQuestionsWithAI,
  summarizeListingWithAI
}));

import { AIAssistantWorkspace } from "@/components/ai-assistant-workspace";

const listing = (id: string, title: string) => ({
  id,
  source_name: "Demo",
  source_url: "https://example.com/listing",
  canonical_url: "https://example.com/listing",
  title,
  description: "Опис квартири",
  deal_type: "rent",
  property_type: "apartment",
  city: "Львів",
  district: "Франківський",
  street: "",
  price_uah: id === "listing-1" ? 15000 : 16500,
  currency: "UAH",
  rooms: 1,
  total_area: "40.00",
  floor: 4,
  floors_total: 9,
  building_type: "new_building",
  renovation_level: "modern",
  heating_type: "individual",
  pets_allowed: true,
  children_allowed: true,
  commission_percent: null,
  is_owner: null,
  images: [],
  attributes: {},
  published_at: "2026-07-17T12:00:00Z",
  is_demo: true,
  user_state: {
    is_favorite: false,
    is_hidden: false,
    is_compared: true,
    note: "",
    updated_at: null
  }
});

const listings = [listing("listing-1", "Квартира №1"), listing("listing-2", "Квартира №2")];


describe("AIAssistantWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchSearchProfiles.mockResolvedValue([
      { id: "profile-1", name: "Біля університету", city: "Львів", is_active: true }
    ]);
    fetchListings.mockResolvedValue({ count: 2, next: null, previous: null, results: listings });
  });

  it("runs profile-aware comparison for the selected apartments", async () => {
    compareListingsWithAI.mockResolvedValue({
      listings: [],
      recommended_listing_id: "listing-2",
      is_decisive: true,
      recommendation: "Квартира №2 краще відповідає вашому профілю.",
      tradeoffs: ["Уточніть заставу."],
      unknowns: ["deposit"],
      confidence: { recommendation: 0.8 },
      meta: { status: "success", provider: "local_rules", model: "local-rules-v1" }
    });

    render(<AIAssistantWorkspace />);

    await screen.findByText("Квартира №1");
    fireEvent.click(screen.getByRole("button", { name: "Порівняти за допомогою AI" }));

    await waitFor(() => {
      expect(compareListingsWithAI).toHaveBeenCalledWith(
        ["listing-1", "listing-2"],
        "profile-1"
      );
    });
    expect(await screen.findByText("Квартира №2 краще відповідає вашому профілю.")).toBeInTheDocument();
    expect(screen.getByText("AI · success · local_rules")).toBeInTheDocument();
  });

  it("generates profile-aware owner questions and copy-ready text", async () => {
    generateOwnerQuestionsWithAI.mockResolvedValue({
      questions: ["Чи можна проживати з дитиною?", "Який розмір застави?"],
      message: "Добрий день! Чи можна проживати з дитиною? Який розмір застави?",
      confidence: { questions: 0.84 },
      meta: { status: "success", provider: "local_rules", model: "local-rules-v1" }
    });

    render(<AIAssistantWorkspace />);

    await screen.findByText("Квартира №1");
    fireEvent.click(screen.getAllByRole("button", { name: "Питання власнику" })[0]);

    await waitFor(() => {
      expect(generateOwnerQuestionsWithAI).toHaveBeenCalledWith("listing-1", "profile-1");
    });
    expect(await screen.findByText("Чи можна проживати з дитиною?")).toBeInTheDocument();
    expect(screen.getByText(/Добрий день!/)).toBeInTheDocument();
  });

  it("shows a validated AI summary without replacing source facts", async () => {
    summarizeListingWithAI.mockResolvedValue({
      summary: "1-кімнатна квартира у Львові за 15 000 грн.",
      advantages: ["Можна з тваринами."],
      caveats: [],
      unknowns: ["Комісія не вказана."],
      confidence: { summary: 0.78 },
      meta: { status: "success", provider: "local_rules", model: "local-rules-v1" }
    });

    render(<AIAssistantWorkspace />);

    await screen.findByText("Квартира №1");
    fireEvent.click(screen.getAllByRole("button", { name: "AI-резюме" })[0]);

    await waitFor(() => {
      expect(summarizeListingWithAI).toHaveBeenCalledWith("listing-1");
    });
    expect(await screen.findByText("1-кімнатна квартира у Львові за 15 000 грн.")).toBeInTheDocument();
    expect(screen.getByText("Комісія не вказана.")).toBeInTheDocument();
  });
});
