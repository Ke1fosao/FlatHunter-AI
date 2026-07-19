import type { ComponentType } from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/search-home", () => ({
  SearchHome: () => <div>Пошуковий огляд</div>,
}));
vi.mock("@/components/cluster-browser", () => ({
  ClusterBrowser: () => <div>Кластеризовані оголошення</div>,
}));
vi.mock("@/components/listing-feed", () => ({
  ListingFeed: () => <div>Кабінет пошуку</div>,
}));
vi.mock("@/components/ai-assistant-workspace", () => ({
  AIAssistantWorkspace: () => <div>AI-помічник</div>,
}));

type Module = { FullSearchExperience: ComponentType };

async function loadComponent(): Promise<Module> {
  const imported: unknown = await import("@/components/full-search-experience");
  return imported as Module;
}

describe("FullSearchExperience", () => {
  it("connects the complete legacy functionality to the search route", async () => {
    const { FullSearchExperience } = await loadComponent();
    render(<FullSearchExperience />);

    expect(screen.getByText("Пошуковий огляд")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /^Оголошення/ }));
    expect(screen.getByText("Кластеризовані оголошення")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /^Кабінет/ }));
    expect(screen.getByText("Кабінет пошуку")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /^AI/ }));
    expect(screen.getByText("AI-помічник")).toBeInTheDocument();
  });

  it("exposes direct navigation to every routed workspace", async () => {
    const { FullSearchExperience } = await loadComponent();
    render(<FullSearchExperience />);

    expect(screen.getByRole("link", { name: "Карта" })).toHaveAttribute("href", "/map");
    expect(screen.getByRole("link", { name: "Обране" })).toHaveAttribute("href", "/favorites");
    expect(screen.getByRole("link", { name: "Порівняння" })).toHaveAttribute("href", "/compare");
    expect(screen.getByRole("link", { name: "Профіль" })).toHaveAttribute("href", "/profile");
  });
});
