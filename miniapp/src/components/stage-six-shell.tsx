"use client";

import { useState } from "react";

import { AIAssistantWorkspace } from "@/components/ai-assistant-workspace";
import { AppShell, type AppNavigationTarget } from "@/components/app-shell";
import { ClusterBrowser } from "@/components/cluster-browser";
import { ListingFeed } from "@/components/listing-feed";
import { MapWorkspace } from "@/components/map-workspace";
import { ProfileWorkspace } from "@/components/profile-workspace";
import { SearchWizard } from "@/components/search-wizard";

type ProductView = "clusters" | "workspace" | "map" | "ai" | "profile";
type WorkspaceTab = "dashboard" | "feed" | "favorites" | "comparison";
type MainNavigation = "search" | "map" | "favorites" | "compare" | "profile";

export function StageSixShell() {
  const [view, setView] = useState<ProductView>("clusters");
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("dashboard");
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState(false);

  const activeNavigation: MainNavigation =
    view === "map"
      ? "map"
      : view === "profile"
        ? "profile"
        : view === "workspace" && workspaceTab === "favorites"
          ? "favorites"
          : view === "workspace" && workspaceTab === "comparison"
            ? "compare"
            : "search";

  const openWorkspace = (tab: WorkspaceTab) => {
    setWorkspaceTab(tab);
    setView("workspace");
  };

  const navigate = (target: AppNavigationTarget) => {
    if (target === "map") {
      setView("map");
      return;
    }
    if (target === "favorites") {
      openWorkspace("favorites");
      return;
    }
    if (target === "compare") {
      openWorkspace("comparison");
      return;
    }
    if (target === "feed") {
      openWorkspace("feed");
      return;
    }
    if (target === "dashboard") {
      openWorkspace("dashboard");
      return;
    }
    if (target === "profile") {
      setView("profile");
      return;
    }
    if (target === "ai") {
      setView("ai");
      return;
    }
    setView("clusters");
  };

  return (
    <>
      <AppShell
        activeNavigation={activeNavigation}
        onCreateSearch={() => {
          setOpen(true);
        }}
        onNavigate={navigate}
      />
      <nav className="stage-six-switch" aria-label="Режим перегляду">
        <button
          type="button"
          className={view === "clusters" ? "is-active" : ""}
          onClick={() => {
            setView("clusters");
          }}
        >
          ≋ Оголошення
        </button>
        <button
          type="button"
          className={view === "workspace" ? "is-active" : ""}
          onClick={() => {
            openWorkspace("dashboard");
          }}
        >
          ▦ Кабінет
        </button>
        <button
          type="button"
          className={view === "map" ? "is-active" : ""}
          onClick={() => {
            setView("map");
          }}
        >
          ◉ Карта
        </button>
        <button
          type="button"
          className={view === "ai" ? "is-active" : ""}
          onClick={() => {
            setView("ai");
          }}
        >
          ✦ AI
        </button>
      </nav>
      {view === "clusters" && <ClusterBrowser />}
      {view === "workspace" && <ListingFeed initialTab={workspaceTab} />}
      {view === "map" && <MapWorkspace />}
      {view === "ai" && <AIAssistantWorkspace />}
      {view === "profile" && (
        <ProfileWorkspace
          onCreateSearch={() => {
            setOpen(true);
          }}
          onNavigate={navigate}
        />
      )}
      <button
        className="stage-six-create"
        type="button"
        onClick={() => {
          setOpen(true);
        }}
      >
        ＋ Створити пошук
      </button>
      {created && (
        <div className="stage-six-toast">✅ Пошуковий профіль створено</div>
      )}
      {open && (
        <SearchWizard
          onClose={() => {
            setOpen(false);
          }}
          onCreated={() => {
            setOpen(false);
            setCreated(true);
            window.dispatchEvent(new Event("flathunter:authenticated"));
            window.setTimeout(() => {
              setCreated(false);
            }, 3000);
          }}
        />
      )}
    </>
  );
}
