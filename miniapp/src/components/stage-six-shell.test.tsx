import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/app-shell", () => ({
  AppShell: ({
    activeNavigation,
    onCreateSearch,
    onNavigate
  }: {
    activeNavigation: string;
    onCreateSearch: () => void;
    onNavigate: (target: string) => void;
  }) => (
    <div>
      <span>Active navigation: {activeNavigation}</span>
      <button type="button" onClick={onCreateSearch}>Hero create</button>
      <button type="button" onClick={() => { onNavigate("search"); }}>Bottom search</button>
      <button type="button" onClick={() => { onNavigate("feed"); }}>Hero demo</button>
      <button type="button" onClick={() => { onNavigate("map"); }}>Bottom map</button>
      <button type="button" onClick={() => { onNavigate("favorites"); }}>Bottom favorites</button>
      <button type="button" onClick={() => { onNavigate("compare"); }}>Bottom compare</button>
      <button type="button" onClick={() => { onNavigate("profile"); }}>Bottom profile</button>
    </div>
  )
}));
vi.mock("@/components/cluster-browser", () => ({
  ClusterBrowser: () => <div>Cluster browser</div>
}));
vi.mock("@/components/listing-feed", () => ({
  ListingFeed: ({ initialTab }: { initialTab?: string }) => <div>Listing workspace: {initialTab ?? "dashboard"}</div>
}));
vi.mock("@/components/map-workspace", () => ({
  MapWorkspace: () => <div>PostGIS map workspace</div>
}));
vi.mock("@/components/ai-assistant-workspace", () => ({
  AIAssistantWorkspace: () => <div>AI workspace</div>
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

  it("wires the main screen and bottom navigation to real product views", () => {
    render(<StageSixShell />);

    fireEvent.click(screen.getByRole("button", { name: "Bottom map" }));
    expect(screen.getByText("PostGIS map workspace")).toBeInTheDocument();
    expect(screen.getByText("Active navigation: map")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bottom favorites" }));
    expect(screen.getByText("Listing workspace: favorites")).toBeInTheDocument();
    expect(screen.getByText("Active navigation: favorites")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bottom compare" }));
    expect(screen.getByText("Listing workspace: comparison")).toBeInTheDocument();
    expect(screen.getByText("Active navigation: compare")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Hero demo" }));
    expect(screen.getByText("Listing workspace: feed")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bottom search" }));
    expect(screen.getByText("Cluster browser")).toBeInTheDocument();
  });

  it("opens create search and profile actions from the main shell", () => {
    render(<StageSixShell />);

    fireEvent.click(screen.getByRole("button", { name: "Hero create" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Search wizard");
    fireEvent.click(screen.getByRole("button", { name: "Закрити" }));

    fireEvent.click(screen.getByRole("button", { name: "Bottom profile" }));
    expect(screen.getByRole("region", { name: "Профіль користувача" })).toBeInTheDocument();
    expect(screen.getByText("Active navigation: profile")).toBeInTheDocument();
  });
});
