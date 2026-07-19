import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();
const source = (path: string): string =>
  readFileSync(join(root, path), "utf8");

describe("full routed Mini App contract", () => {
  it("keeps every user route behind the shared Telegram auth gate", () => {
    const shell = source("src/components/miniapp-shell.tsx");
    expect(shell).toContain("<AuthGate>{children}</AuthGate>");
    expect(shell.match(/<BottomNavigation/g)).toHaveLength(1);
  });

  it("uses the full cluster-aware search workspace", () => {
    const search = source("src/components/search-home.tsx");
    const results = source("src/components/search-results-workspace.tsx");
    expect(search).toContain("<SearchResultsWorkspace");
    expect(results).toContain("fetchClusterFeed");
    expect(results).toContain("setClusterState");
    expect(results).toContain("Мінімальна ціна");
    expect(results).toContain("Максимальна ціна");
    expect(results).toContain("Текст");
  });

  it("keeps cluster sources and persisted notes on listing details", () => {
    const page = source("src/app/(miniapp)/listings/[id]/page.tsx");
    const extras = source("src/components/cluster-detail-extras.tsx");
    const notes = source("src/components/cluster-note-editor.tsx");
    expect(page).toContain("ClusterDetailExtras");
    expect(extras).toContain("<ClusterSources cluster={cluster}");
    expect(notes).toContain("setClusterState(clusterId, { note })");
  });

  it("persists notification settings in backend search profiles", () => {
    const profile = source("src/components/profile-workspace.tsx");
    const wizard = source("src/components/search-wizard.tsx");
    expect(profile).toContain("<SearchProfileManager");
    expect(profile).not.toContain("flathunter-notifications");
    expect(wizard).toContain("updateSearchProfile(profile.id, payload)");
    expect(wizard).toContain("notification_preference");
  });

  it("limits comparison to four backend-supported cluster slots", () => {
    const comparison = source("src/components/comparison-workspace.tsx");
    expect(comparison).toContain(".slice(0, 4)");
    expect(comparison).toContain("compareListingsWithAI");
    expect(comparison).toContain("profileId || undefined");
    expect(comparison).not.toContain(".slice(0, 5)");
  });
});
