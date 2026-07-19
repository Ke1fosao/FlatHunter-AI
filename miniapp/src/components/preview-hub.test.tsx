import type { ComponentType } from "react";

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

type Module = { PreviewHub: ComponentType };

async function loadComponent(): Promise<Module> {
  const imported: unknown = await import("@/components/preview-hub");
  return imported as Module;
}

function requiredButton(button: HTMLElement | undefined, label: string): HTMLElement {
  if (!button) {
    throw new Error(`${label} button was not rendered`);
  }
  return button;
}

describe("PreviewHub", () => {
  it("renders all primary product areas instead of an empty browser screen", async () => {
    const { PreviewHub } = await loadComponent();
    render(<PreviewHub />);

    expect(
      screen.getByRole("heading", { name: "Повна демо-версія FlatHunter" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Пошук" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Карта" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Обране" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Порівняння" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AI" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Профіль" })).toBeInTheDocument();
  });

  it("supports creating a search profile and saving it in browser preview state", async () => {
    const { PreviewHub } = await loadComponent();
    render(<PreviewHub />);

    fireEvent.click(screen.getByRole("button", { name: "Створити пошук" }));
    fireEvent.change(screen.getByLabelText("Назва пошуку"), {
      target: { value: "Квартира біля центру" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Зберегти пошук" }));

    expect(screen.getByText("Квартира біля центру")).toBeInTheDocument();
  });

  it("keeps favorite and comparison actions interactive in preview mode", async () => {
    const { PreviewHub } = await loadComponent();
    render(<PreviewHub />);

    const favoriteButton = requiredButton(
      screen.getAllByRole("button", { name: "В обране" }).at(0),
      "favorite",
    );
    fireEvent.click(favoriteButton);
    fireEvent.click(screen.getByRole("button", { name: /^Обране/ }));
    expect(screen.getByText("Світла квартира біля Стрийського парку")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Пошук" }));
    const compareButtons = screen.getAllByRole("button", { name: "Порівняти" });
    fireEvent.click(requiredButton(compareButtons.at(0), "first compare"));
    fireEvent.click(requiredButton(compareButtons.at(1), "second compare"));
    fireEvent.click(screen.getByRole("button", { name: /^Порівняння/ }));

    expect(screen.getByRole("heading", { name: "Порівняння квартир" })).toBeInTheDocument();
  });
});
