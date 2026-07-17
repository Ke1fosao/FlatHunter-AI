"use client";

import { useState } from "react";

import { AIAssistantWorkspace } from "@/components/ai-assistant-workspace";
import { AppShell } from "@/components/app-shell";
import { ClusterBrowser } from "@/components/cluster-browser";
import { ListingFeed } from "@/components/listing-feed";
import { MapWorkspace } from "@/components/map-workspace";
import { SearchWizard } from "@/components/search-wizard";

type ProductView = "clusters" | "workspace" | "map" | "ai";

export function StageSixShell() {
  const [view, setView] = useState<ProductView>("clusters");
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState(false);

  return (
    <>
      <AppShell />
      <nav className="stage-six-switch" aria-label="Режим перегляду">
        <button
          type="button"
          className={view === "clusters" ? "is-active" : ""}
          onClick={() => { setView("clusters"); }}
        >
          ≋ Оголошення
        </button>
        <button
          type="button"
          className={view === "workspace" ? "is-active" : ""}
          onClick={() => { setView("workspace"); }}
        >
          ▦ Кабінет
        </button>
        <button
          type="button"
          className={view === "map" ? "is-active" : ""}
          onClick={() => { setView("map"); }}
        >
          ◉ Карта
        </button>
        <button
          type="button"
          className={view === "ai" ? "is-active" : ""}
          onClick={() => { setView("ai"); }}
        >
          ✦ AI
        </button>
      </nav>
      {view === "clusters" && <ClusterBrowser />}
      {view === "workspace" && <ListingFeed />}
      {view === "map" && <MapWorkspace />}
      {view === "ai" && <AIAssistantWorkspace />}
      <button className="stage-six-create" type="button" onClick={() => { setOpen(true); }}>
        ＋ Створити пошук
      </button>
      {created && <div className="stage-six-toast">✅ Пошуковий профіль створено</div>}
      {open && (
        <SearchWizard
          onClose={() => { setOpen(false); }}
          onCreated={() => {
            setOpen(false);
            setCreated(true);
            window.dispatchEvent(new Event("flathunter:authenticated"));
            window.setTimeout(() => { setCreated(false); }, 3000);
          }}
        />
      )}
    </>
  );
}
