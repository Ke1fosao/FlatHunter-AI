import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/app-shell", () => ({
  AppShell: () => <div>App shell</div>
}));
vi.mock("@/components/cluster-browser", () => ({
  ClusterBrowser: () => <div>Cluster browser</div>
}));
vi.mock("@/components/listing-feed", () => ({
  ListingFeed: () => <div>Listing workspace</div>
}));
vi.mock("@/components/map-workspace", () => ({
  MapWorkspace: () => <div>PostGIS map workspace</div>
}));
vi.mock("@/components/search-wizard", () => ({
  SearchWizard: ({ onClose }: { onClose: () => void }) => (
    <div role="dialog">
      Search wizard
      <button type="button" onClick={onClose}>Закрити</button>
    </div>
  )
}));

import { StageSixShell } from "@/components/stage-six-shell";

describe("StageSixShell", () => {
  it("switches between the cluster workspace and the map", () => {
    render(<StageSixShell />);

    expect(screen.getByText("Cluster browser")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "◉ Карта" }));

    expect(screen.getByText("PostGIS map workspace")).toBeInTheDocument();
    expect(screen.queryByText("Cluster browser")).not.toBeInTheDocument();
  });

  it("opens and closes the search wizard", () => {
    render(<StageSixShell />);

    fireEvent.click(screen.getByRole("button", { name: "＋ Створити пошук" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Search wizard");

    fireEvent.click(screen.getByRole("button", { name: "Закрити" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
