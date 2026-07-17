import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  fetchMarketAnalysis,
  fetchPriceHistory,
  fetchRiskAnalysis,
  refreshListingAnalysis
} = vi.hoisted(() => ({
  fetchMarketAnalysis: vi.fn(),
  fetchPriceHistory: vi.fn(),
  fetchRiskAnalysis: vi.fn(),
  refreshListingAnalysis: vi.fn()
}));

vi.mock("@/lib/analysis-api", () => ({
  fetchMarketAnalysis,
  fetchPriceHistory,
  fetchRiskAnalysis,
  refreshListingAnalysis
}));

import { AnalysisChips, ListingAnalysisPanel } from "@/components/listing-analysis-panel";

const summary = {
  market: {
    status: "ready" as const,
    median_price_uah: 18000,
    q1_price_uah: 16500,
    q3_price_uah: 19500,
    deviation_percent: "-8.33",
    comparable_count: 23,
    confidence_label: "high" as const,
    calculated_at: "2026-07-17T12:00:00Z"
  },
  risk: {
    status: "ready" as const,
    score: 34,
    level: "review" as const,
    summary: "Є моменти, які варто додатково перевірити.",
    calculated_at: "2026-07-17T12:00:00Z"
  },
  latest_price_change: {
    previous_price_uah: 18000,
    new_price_uah: 16500,
    change_amount_uah: -1500,
    change_percent: "-8.33",
    direction: "decrease" as const,
    changed_at: "2026-07-17T12:00:00Z"
  }
};

function mockReady(): void {
  fetchMarketAnalysis.mockResolvedValue({
    listing_id: "listing-1",
    current_price_uah: 16500,
    assessment: {
      id: "market-1",
      status: "ready",
      provider: "local",
      algorithm_version: "market-v1",
      median_price_uah: 18000,
      q1_price_uah: 16500,
      q3_price_uah: 19500,
      median_price_per_sqm: "450.00",
      target_price_per_sqm: "412.50",
      deviation_percent: "-8.33",
      comparable_count: 23,
      confidence_score: "82.00",
      confidence_label: "high",
      selection_summary: {},
      explanation: "Використано 23 схожі оголошення.",
      calculated_at: "2026-07-17T12:00:00Z",
      valid_until: "2026-07-18T12:00:00Z",
      is_stale: false
    }
  });
  fetchRiskAnalysis.mockResolvedValue({
    listing_id: "listing-1",
    assessment: {
      id: "risk-1",
      status: "ready",
      score: 34,
      level: "review",
      signals: [{
        code: "price_below_market",
        weight: 18,
        severity: "medium",
        evidence: { deviation_percent: "-8.33" },
        label: "Ціна нижча за схожі оголошення",
        recommendation: "З'ясуйте причину нижчої ціни."
      }],
      protective_signals: [],
      summary: "Є моменти, які варто додатково перевірити.",
      safety_advice: "Перевірте документи та не переказуйте кошти до перегляду.",
      algorithm_version: "risk-v1",
      calculated_at: "2026-07-17T12:00:00Z",
      valid_until: "2026-07-18T12:00:00Z",
      is_stale: false
    },
    disclaimer: "Допоміжна оцінка, не юридичний висновок."
  });
  fetchPriceHistory.mockResolvedValue({
    listing_id: "listing-1",
    current_price_uah: 16500,
    events: [{
      id: "event-1",
      previous_price_uah: 18000,
      new_price_uah: 16500,
      change_amount_uah: -1500,
      change_percent: "-8.33",
      direction: "decrease",
      changed_at: "2026-07-17T12:00:00Z",
      detected_at: "2026-07-17T12:01:00Z"
    }]
  });
}

describe("ListingAnalysisPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReady();
  });

  it("shows price, market confidence, textual risk and accessible history", async () => {
    render(<ListingAnalysisPanel listingId="listing-1" summary={summary} />);

    expect(await screen.findByText(/16 500 грн–19 500 грн/)).toBeInTheDocument();
    expect(screen.getByText(/аналогів: 23/)).toBeInTheDocument();
    expect(screen.getByText("34/100")).toBeInTheDocument();
    expect(screen.getByText("Ціна нижча за схожі оголошення")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Історія ціни квартири" })).toBeInTheDocument();
    expect(screen.getByLabelText("Текстова історія ціни")).toHaveTextContent("18 000 грн → 16 500 грн");
    expect(screen.getByText("Допоміжна оцінка, не юридичний висновок.")).toBeInTheDocument();
  });

  it("renders compact chips without relying on color alone", () => {
    render(<AnalysisChips summary={summary} />);

    expect(screen.getByText(/↓ 8.3% ціна/)).toBeInTheDocument();
    expect(screen.getByText(/Ринок: нижче на 8%/)).toBeInTheDocument();
    expect(screen.getByText(/Є моменти для перевірки · 34\/100/)).toBeInTheDocument();
  });

  it("refreshes through the authenticated endpoint and reloads data", async () => {
    refreshListingAnalysis.mockResolvedValue({ market: {}, risk: {} });
    render(<ListingAnalysisPanel listingId="listing-1" />);

    await screen.findByText("34/100");
    fireEvent.click(screen.getByRole("button", { name: "Оновити" }));

    await waitFor(() => { expect(refreshListingAnalysis).toHaveBeenCalledTimes(1); });
    await waitFor(() => { expect(fetchMarketAnalysis).toHaveBeenCalledTimes(2); });
  });

  it("shows a user-safe error state", async () => {
    fetchMarketAnalysis.mockRejectedValue(new Error("network"));
    render(<ListingAnalysisPanel listingId="listing-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Не вдалося завантажити аналітику квартири.");
  });
});
