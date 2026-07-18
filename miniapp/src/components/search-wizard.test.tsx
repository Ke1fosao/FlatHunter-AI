import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createSearchProfile: vi.fn(),
  parseNaturalLanguageSearch: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  createSearchProfile: mocks.createSearchProfile,
  parseNaturalLanguageSearch: mocks.parseNaturalLanguageSearch,
}));

import { SearchWizard } from "@/components/search-wizard";

describe("SearchWizard modal lifecycle", () => {
  beforeEach(() => {
    mocks.createSearchProfile.mockReset();
    mocks.parseNaturalLanguageSearch.mockReset();
    document.body.style.overflow = "auto";
  });

  afterEach(() => {
    document.body.style.overflow = "";
  });

  it("closes when the backdrop itself is clicked", () => {
    const onClose = vi.fn();
    const { container } = render(
      <SearchWizard onClose={onClose} onCreated={vi.fn()} />,
    );
    const backdrop = container.querySelector<HTMLElement>(".wizard-backdrop");

    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop as HTMLElement);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when the dialog content is clicked", () => {
    const onClose = vi.fn();
    render(<SearchWizard onClose={onClose} onCreated={vi.fn()} />);

    fireEvent.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes when Escape is pressed", () => {
    const onClose = vi.fn();
    render(<SearchWizard onClose={onClose} onCreated={vi.fn()} />);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("locks page scrolling and restores the previous overflow value", () => {
    document.body.style.overflow = "clip";
    const { unmount } = render(
      <SearchWizard onClose={vi.fn()} onCreated={vi.fn()} />,
    );

    expect(document.body.style.overflow).toBe("hidden");

    unmount();

    expect(document.body.style.overflow).toBe("clip");
  });
});
