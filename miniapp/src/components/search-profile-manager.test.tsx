import type { ComponentType } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const profile = {
  id: "profile-1",
  name: "Львів · 1 кімната",
  city: "Львів",
  deal_type: "rent" as const,
  price_min: 12000,
  price_max: 18000,
  currency: "UAH",
  rooms: [1],
  desired_districts: ["Франківський"],
  excluded_districts: [],
  move_in_date: null,
  occupants: 1,
  children: false,
  pets: { cat: true },
  property_types: ["apartment"],
  filters: { exclude_first_floor: true },
  is_active: true,
  source_text: "",
  important_places: [],
  notification_preference: {
    id: "notification-1",
    frequency: "instant" as const,
    min_match_score: 75,
    max_risk_score: 70,
    daily_limit: 20,
    quiet_hours_enabled: true,
    quiet_hours_start: "23:00:00",
    quiet_hours_end: "08:00:00",
    notify_price_changes: true,
    notify_reactivated: false,
    updated_at: "2026-07-19T00:00:00Z",
  },
  created_at: "2026-07-19T00:00:00Z",
  updated_at: "2026-07-19T00:00:00Z",
};

const mocks = vi.hoisted(() => ({
  fetchSearchProfiles: vi.fn(),
  pauseSearchProfile: vi.fn(),
  activateSearchProfile: vi.fn(),
  deleteSearchProfile: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  fetchSearchProfiles: mocks.fetchSearchProfiles,
  pauseSearchProfile: mocks.pauseSearchProfile,
  activateSearchProfile: mocks.activateSearchProfile,
  deleteSearchProfile: mocks.deleteSearchProfile,
}));

vi.mock("@/components/search-wizard", () => ({
  SearchWizard: ({
    profile: selectedProfile,
    onSaved,
  }: {
    profile?: { name: string };
    onSaved?: () => void;
  }) => (
    <div role="dialog">
      <span>{selectedProfile?.name ?? "Новий пошук"}</span>
      <button type="button" onClick={onSaved}>
        Save mocked profile
      </button>
    </div>
  ),
}));

type ManagerModule = {
  SearchProfileManager: ComponentType<{ compact?: boolean }>;
};

async function loadManager(): Promise<ManagerModule> {
  const imported: unknown = await import("@/components/search-profile-manager");
  return imported as ManagerModule;
}

describe("SearchProfileManager", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mocks.fetchSearchProfiles.mockReset().mockResolvedValue([profile]);
    mocks.pauseSearchProfile.mockReset().mockResolvedValue({
      ...profile,
      is_active: false,
    });
    mocks.activateSearchProfile.mockReset().mockResolvedValue(profile);
    mocks.deleteSearchProfile.mockReset().mockResolvedValue(undefined);
  });

  it("loads full profiles and opens the selected profile for editing", async () => {
    const { SearchProfileManager } = await loadManager();
    render(<SearchProfileManager />);

    expect(await screen.findByText("Львів · 1 кімната")).toBeInTheDocument();
    expect(screen.getByText(/12 000–18 000 грн/)).toBeInTheDocument();
    expect(screen.getByText("Match від 75%")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Редагувати" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Львів · 1 кімната");
  });

  it("pauses an active profile and reloads server state", async () => {
    const { SearchProfileManager } = await loadManager();
    render(<SearchProfileManager />);

    fireEvent.click(await screen.findByRole("button", { name: "Призупинити" }));

    await waitFor(() => {
      expect(mocks.pauseSearchProfile).toHaveBeenCalledWith("profile-1");
      expect(mocks.fetchSearchProfiles).toHaveBeenCalledTimes(2);
    });
  });

  it("activates a paused profile", async () => {
    mocks.fetchSearchProfiles.mockResolvedValue([{ ...profile, is_active: false }]);
    const { SearchProfileManager } = await loadManager();
    render(<SearchProfileManager />);

    fireEvent.click(await screen.findByRole("button", { name: "Активувати" }));

    await waitFor(() => {
      expect(mocks.activateSearchProfile).toHaveBeenCalledWith("profile-1");
    });
  });

  it("requires explicit confirmation before deletion", async () => {
    const { SearchProfileManager } = await loadManager();
    render(<SearchProfileManager />);

    fireEvent.click(await screen.findByRole("button", { name: "Видалити" }));
    expect(mocks.deleteSearchProfile).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Так, видалити пошук" }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Так, видалити пошук" }),
    );

    await waitFor(() => {
      expect(mocks.deleteSearchProfile).toHaveBeenCalledWith("profile-1");
    });
  });

  it("reloads profiles after wizard save", async () => {
    const { SearchProfileManager } = await loadManager();
    render(<SearchProfileManager />);

    fireEvent.click(await screen.findByRole("button", { name: "Редагувати" }));
    fireEvent.click(screen.getByRole("button", { name: "Save mocked profile" }));

    await waitFor(() => {
      expect(mocks.fetchSearchProfiles).toHaveBeenCalledTimes(2);
    });
  });
});
