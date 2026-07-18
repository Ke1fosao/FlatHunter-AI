import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchBackendHealth = vi.fn();
const authenticateTelegram = vi.fn();
const triggerSelectionFeedback = vi.fn();

vi.mock("@/hooks/use-telegram", () => ({
  useTelegram: () => ({
    initData: "",
    firstName: "Дмитро",
    languageCode: "uk",
    colorScheme: "dark",
    isTelegram: true,
  }),
}));

vi.mock("@/lib/api", () => ({
  fetchBackendHealth: (...args: unknown[]) => fetchBackendHealth(...args),
  authenticateTelegram: (...args: unknown[]) => authenticateTelegram(...args),
}));

vi.mock("@/lib/telegram", () => ({
  triggerSelectionFeedback: () => triggerSelectionFeedback(),
}));

import { AppShell, type AppNavigationTarget } from "@/components/app-shell";

describe("AppShell navigation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchBackendHealth.mockResolvedValue({
      status: "ready",
      checks: { database: "ok", cache: "ok" },
    });
    authenticateTelegram.mockReset();
    triggerSelectionFeedback.mockReset();
  });

  it("connects every primary visible action to its intended product destination", () => {
    const onCreateSearch = vi.fn();
    const onNavigate = vi.fn<(target: AppNavigationTarget) => void>();

    render(
      <AppShell
        activeNavigation="search"
        onCreateSearch={onCreateSearch}
        onNavigate={onNavigate}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /створити пошук/i }));
    expect(onCreateSearch).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /запустити демо/i }));
    expect(onNavigate).toHaveBeenLastCalledWith("feed");

    fireEvent.click(screen.getByRole("button", { name: /налаштувати/i }));
    expect(onNavigate).toHaveBeenLastCalledWith("dashboard");

    fireEvent.click(screen.getByRole("button", { name: /переглянути квартиру/i }));
    expect(onNavigate).toHaveBeenLastCalledWith("feed");

    fireEvent.click(screen.getByRole("button", { name: "Карта" }));
    expect(onNavigate).toHaveBeenLastCalledWith("map");

    fireEvent.click(screen.getByRole("button", { name: "Порівняння" }));
    expect(onNavigate).toHaveBeenLastCalledWith("compare");

    fireEvent.click(screen.getByRole("button", { name: "Профіль" }));
    expect(onNavigate).toHaveBeenLastCalledWith("profile");
  });
});
