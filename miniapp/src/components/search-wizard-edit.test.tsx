import type { ComponentType } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const profile = {
  id: "profile-1",
  name: "Старий пошук",
  city: "Львів",
  deal_type: "rent" as const,
  price_min: 10000,
  price_max: 18000,
  currency: "UAH",
  rooms: [1],
  desired_districts: ["Франківський"],
  excluded_districts: ["Залізничний"],
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
    frequency: "hourly" as const,
    min_match_score: 80,
    max_risk_score: 60,
    daily_limit: 12,
    quiet_hours_enabled: true,
    quiet_hours_start: "22:30:00",
    quiet_hours_end: "08:30:00",
    notify_price_changes: true,
    notify_reactivated: true,
    updated_at: "2026-07-19T00:00:00Z",
  },
  created_at: "2026-07-19T00:00:00Z",
  updated_at: "2026-07-19T00:00:00Z",
};

const mocks = vi.hoisted(() => ({
  createSearchProfile: vi.fn(),
  updateSearchProfile: vi.fn(),
  parseNaturalLanguageSearch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  createSearchProfile: mocks.createSearchProfile,
  updateSearchProfile: mocks.updateSearchProfile,
  parseNaturalLanguageSearch: mocks.parseNaturalLanguageSearch,
}));

type WizardProps = {
  onClose: () => void;
  onCreated?: () => void;
  onSaved?: () => void;
  profile?: typeof profile;
};

type WizardModule = {
  SearchWizard: ComponentType<WizardProps>;
};

type SavedProfilePayload = {
  name: string;
  price_min?: number | null;
  price_max?: number | null;
  desired_districts: string[];
  excluded_districts: string[];
  notification_preference: {
    frequency: string;
    min_match_score: number;
    daily_limit: number;
  };
};

async function loadWizard(): Promise<WizardModule> {
  const imported: unknown = await import("@/components/search-wizard");
  return imported as WizardModule;
}

describe("SearchWizard edit mode", () => {
  beforeEach(() => {
    mocks.createSearchProfile.mockReset();
    mocks.updateSearchProfile.mockReset().mockResolvedValue(profile);
    mocks.parseNaturalLanguageSearch.mockReset();
  });

  it("prefills every persisted field and saves with PATCH", async () => {
    const { SearchWizard } = await loadWizard();
    const onSaved = vi.fn();
    render(
      <SearchWizard
        profile={profile}
        onClose={vi.fn()}
        onSaved={onSaved}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Редагувати пошук" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Назва пошуку")).toHaveValue("Старий пошук");
    expect(screen.getByLabelText("Мінімальна ціна")).toHaveValue(10000);
    expect(screen.getByLabelText("Максимальна ціна")).toHaveValue(18000);
    expect(screen.getByLabelText("Бажані райони")).toHaveValue("Франківський");
    expect(screen.getByLabelText("Виключені райони")).toHaveValue("Залізничний");

    fireEvent.change(screen.getByLabelText("Назва пошуку"), {
      target: { value: "Оновлений пошук" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Продовжити" }));
    fireEvent.click(screen.getByRole("button", { name: "Продовжити" }));
    fireEvent.click(screen.getByRole("button", { name: "Зберегти зміни" }));

    await waitFor(() => {
      expect(mocks.updateSearchProfile).toHaveBeenCalledTimes(1);
      expect(onSaved).toHaveBeenCalledTimes(1);
    });
    const calls = mocks.updateSearchProfile.mock.calls as unknown as Array<
      [string, SavedProfilePayload]
    >;
    const call = calls.at(0);
    expect(call?.[0]).toBe("profile-1");
    expect(call?.[1]).toMatchObject({
      name: "Оновлений пошук",
      price_min: 10000,
      price_max: 18000,
      desired_districts: ["Франківський"],
      excluded_districts: ["Залізничний"],
      notification_preference: {
        frequency: "hourly",
        min_match_score: 80,
        daily_limit: 12,
      },
    });
    expect(mocks.createSearchProfile).not.toHaveBeenCalled();
  });
});
