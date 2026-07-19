import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ pathname: "/search" }));

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
}));

import { BottomNavigation } from "@/components/bottom-navigation";

describe("BottomNavigation", () => {
  beforeEach(() => {
    mocks.pathname = "/search";
  });

  it("uses real routes for all five primary sections", () => {
    render(<BottomNavigation />);

    expect(screen.getByRole("link", { name: "Пошук" })).toHaveAttribute(
      "href",
      "/search",
    );
    expect(screen.getByRole("link", { name: "Карта" })).toHaveAttribute(
      "href",
      "/map",
    );
    expect(screen.getByRole("link", { name: "Обране" })).toHaveAttribute(
      "href",
      "/favorites",
    );
    expect(screen.getByRole("link", { name: "Порівняння" })).toHaveAttribute(
      "href",
      "/compare",
    );
    expect(screen.getByRole("link", { name: "Профіль" })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  it("derives the active item from the pathname", () => {
    mocks.pathname = "/favorites";
    render(<BottomNavigation />);

    expect(screen.getByRole("link", { name: "Обране" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Пошук" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("keeps search active on listing detail routes", () => {
    mocks.pathname = "/listings/demo-listing";
    render(<BottomNavigation />);

    expect(screen.getByRole("link", { name: "Пошук" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
